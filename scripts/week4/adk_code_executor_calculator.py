"""
Week 4 · ADK 代码执行 Agent / LlmAgent + BuiltInCodeExecutor
============================================================

用 Google ADK 的 LlmAgent + BuiltInCodeExecutor 构造一个计算器 Agent：
  - 收到数学表达式时，Agent 编写 Python 代码并执行，返回数值结果
  - BuiltInCodeExecutor：ADK 的内置代码执行器
  - runner.run_async 异步流式取事件，打印生成的代码 / 执行结果 / 最终文本

核心知识点：
  1. LlmAgent + code_executor：把「写代码 + 跑代码」能力挂到 Agent 上
  2. 事件流里 part.executable_code / part.code_execution_result / part.text 三种片段
  3. event.is_final_response() 判定最终回复

说明：原版用 gemini-2.0-flash + BuiltInCodeExecutor，本仓库无 Gemini key，故：
  1. 模型改用 DeepSeek（LiteLlm）；
  2. BuiltInCodeExecutor 依赖 Gemini 原生代码执行，对非 Gemini 模型直接报错
     （built_in_code_executor.py:54 "not supported for model ..."），故换成 ADK 自带的
     UnsafeLocalCodeExecutor--模型无关，在本地直接 exec 生成的 Python 代码。
     （Unsafe = 无沙箱，仅在受控 demo 中使用；生产应换成 VertexAiCodeExecutor 等沙箱方案。）
教学要点（LLM 写代码 -> 执行器跑 -> 事件流回传代码与结果）完全保留。
知识块：② Agent 核心机制 · ⑥ 工具使用（代码执行）
"""

import asyncio
import os
import sys
from pathlib import Path

import nest_asyncio
from dotenv import load_dotenv

# --- litellm/ADK 环境前置（agent-training 项目本机） ---
# 加载 .env（DeepSeek key 等）
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
# litellm import 期会拉 GitHub 成本表 + Azure tiktoken 词表，本机走代理会卡死；
# 用本地成本表 + 本地 cl100k_base 缓存绕过，无需联网（DeepSeek completion 国内直连）
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("LITELLM_TELEMETRY", "False")
os.environ.setdefault("CUSTOM_TIKTOKEN_CACHE_DIR", str(Path.home() / ".cache" / "tiktoken"))

from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService  # noqa: E402
from google.adk.code_executors import UnsafeLocalCodeExecutor  # noqa: E402
from google.adk.models.lite_llm import LiteLlm  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

APP_NAME = "calculator"
USER_ID = "user1234"
SESSION_ID = "session_code_exec_async"


def _llm():
    """DeepSeek 经 LiteLlm 接入（OpenAI 兼容）。"""
    return LiteLlm(
        model="openai/" + os.environ["DEEPSEEK_MODEL"],
        api_base=os.environ["DEEPSEEK_BASE_URL"],
        api_key=os.environ["DEEPSEEK_API_KEY"],
    )


code_agent = LlmAgent(
    name="calculator_agent",
    model=_llm(),
    code_executor=UnsafeLocalCodeExecutor(),
    instruction="""你是一个计算器 Agent。
    收到数学表达式时，在回复中写一个 ```python 代码块（用 print() 打印计算结果），写完即停止，不要解释。
    系统会自动执行该代码块并把输出回传给你，你随后只回复最终的数值结果。""",
    description="执行 Python 代码完成计算。",
)


async def call_agent_async(query):
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    runner = Runner(
        agent=code_agent,
        app_name=APP_NAME,
        session_service=session_service,
        artifact_service=InMemoryArtifactService(),
    )

    content = types.Content(role='user', parts=[types.Part(text=query)])
    print(f"\n--- 运行查询：{query} ---")
    try:
        async for event in runner.run_async(
            user_id=USER_ID, session_id=SESSION_ID, new_message=content
        ):
            if not (event.content and event.content.parts):
                continue
            # 代码执行过程的片段（生成代码 / 执行结果）可能在非 final 事件里，一律打印
            for part in event.content.parts:
                if part.executable_code:
                    print(f"  调试：生成代码:\n```python\n{part.executable_code.code}\n```")
                elif part.code_execution_result:
                    print(f"  调试：代码执行结果：{part.code_execution_result.outcome} - 输出:\n{part.code_execution_result.output}")
                elif part.text and not part.text.isspace():
                    print(f"  文本：'{part.text.strip()}'")
            if event.is_final_response():
                text_parts = [part.text for part in event.content.parts if part.text and not part.text.isspace()]
                if text_parts:
                    print(f"==> Agent 最终回复：{''.join(text_parts)}")
    except Exception as e:
        print(f"运行出错：{e}")
    print("-" * 30)


async def main():
    await call_agent_async("计算 (5 + 7) * 3 的值")
    await call_agent_async("10 的阶乘是多少？")


if __name__ == "__main__":
    nest_asyncio.apply()
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            print("\n已在事件循环环境（如 Colab/Jupyter）运行。请直接用 `await main()`。")
        else:
            raise e
    # litellm/httpx 关闭期偶发 segfault（exit 139），结果已全部打印，直接干净退出
    sys.stdout.flush()
    os._exit(0)
