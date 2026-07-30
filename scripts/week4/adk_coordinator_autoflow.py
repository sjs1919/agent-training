"""
Week 4 · 补缺 - Google ADK 协调者 / sub_agents 自动委托（Auto-Flow）
=====================================================================

用 Google ADK 的 Agent(sub_agents=...) 实现「协调者 + 子智能体」自动流转，
对标前一个 RunnableBranch 版本，但委托由 ADK 框架自动完成：
  Coordinator（父）- 只做意图识别，调用框架注入的 transfer_to_agent 工具
  Booker（子）      - 机票/酒店预订，带 booking_handler 工具
  Info（子）        - 一般信息，带 info_handler 工具

核心知识点：
  1. Agent(sub_agents=[...]) 声明父子关系，ADK 自动注入 transfer_to_agent 工具
  2. 父 agent 的 instruction 描述「何时委托给哪个子 agent」，模型自行决定调用
  3. FunctionTool 把普通函数包成 agent 可调用的工具
  4. InMemoryRunner + session 驱动单轮多步流转（父委托 -> 子执行 -> 子回最终响应）

适配说明（原版用 gemini-2.0-flash，本仓库无 Gemini key）：
  改用 DeepSeek（OpenAI 兼容）经 ADK LiteLlm 接入。ADK 的 LiteLlm 对 DeepSeek
  有专门的内联 tool-call 解析，function-calling 一等支持。
环境前置（本机出网必须走 Clash 代理，且 litellm 默认会联网拉词表/成本表）：
  - HTTPS_PROXY/HTTP_PROXY 指向 Clash（DeepSeek 国内 API 也经此）
  - LITELLM_LOCAL_MODEL_COST_MAP=True：跳过从 GitHub 拉模型成本表
  - LITELLM_TELEMETRY=False：关遥测
  - CUSTOM_TIKTOKEN_CACHE_DIR 指向本地缓存（~/.cache/tiktoken/）：用真 cl100k_base
    词表本地副本，绕过 litellm import 时从 Azure blob 联网下载（走代理极慢）
知识块：⑧ Agent 集群 · ② Agent 核心机制 · ④ MCP（工具调用）
"""

import os
from pathlib import Path

# ============================================================
# 环境前置：必须在 import litellm / google.adk 之前生效
# ============================================================
# 1) 代理：本机出网走 Clash（端口 3450）。Clash 需先开启。
os.environ.setdefault("HTTPS_PROXY", "http://127.0.0.1:3450")
os.environ.setdefault("HTTP_PROXY", "http://127.0.0.1:3450")
# 2) litellm：只用本地成本表、关遥测，避免 import 时联网卡死
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("LITELLM_TELEMETRY", "False")

# 3) tiktoken cl100k_base 词表：litellm import 时会从 Azure blob 拉它，走代理极慢。
#    已把真词表放到本地缓存目录，设 CUSTOM_TIKTOKEN_CACHE_DIR 让 litellm 用本地副本。
#    缓存文件名 = sha1(词表 URL) = 9b5ad71b2ce5302211f9c61530b329a4922fc6a4
os.environ.setdefault(
    "CUSTOM_TIKTOKEN_CACHE_DIR", str(Path.home() / ".cache" / "tiktoken")
)

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

import uuid
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.adk.models.lite_llm import LiteLlm
from google.genai import types


# --- DeepSeek via LiteLLM（OpenAI 兼容端点） ---
def _llm() -> LiteLlm:
    return LiteLlm(
        model="openai/" + os.environ["DEEPSEEK_MODEL"],
        api_base=os.environ["DEEPSEEK_BASE_URL"],
        api_key=os.environ["DEEPSEEK_API_KEY"],
    )


# --- 定义工具函数 ---
def booking_handler(request: str) -> str:
    """
    处理机票和酒店预订请求。
    Args:
        request: 用户的预订请求。
    Returns:
        预订处理确认信息。
    """
    print("-------------------------- 预订处理器已调用 ----------------------------")
    return f"已模拟处理预订请求：'{request}'。"


def info_handler(request: str) -> str:
    """
    处理一般信息请求。
    Args:
        request: 用户问题。
    Returns:
        信息检索处理结果。
    """
    print("-------------------------- 信息处理器已调用 ----------------------------")
    return f"信息请求：'{request}'。结果：模拟信息检索。"


def unclear_handler(request: str) -> str:
    """处理无法委托的请求。"""
    return f"协调者无法委托请求：'{request}'。请补充说明。"


# --- 创建工具 ---
booking_tool = FunctionTool(booking_handler)
info_tool = FunctionTool(info_handler)

# 定义配备工具的专用子智能体
booking_agent = Agent(
    name="Booker",
    model=_llm(),
    description="专门处理机票和酒店预订请求，通过 booking tool 实现。",
    tools=[booking_tool],
)

info_agent = Agent(
    name="Info",
    model=_llm(),
    description="专门提供一般信息和答疑，通过 info tool 实现。",
    tools=[info_tool],
)

# 定义父智能体（协调者），包含委托指令
coordinator = Agent(
    name="Coordinator",
    model=_llm(),
    instruction=(
        "你是主协调者，只负责分析用户请求并委托给合适的专用智能体。"
        "不要直接回答用户。\n"
        "- 任何涉及机票或酒店预订的请求，委托给 'Booker' 智能体。\n"
        "- 其他一般信息问题，委托给 'Info' 智能体。"
    ),
    description="负责将用户请求路由到正确专用智能体的协调者。",
    sub_agents=[booking_agent, info_agent],
)

# --- 执行逻辑 ---


async def run_coordinator(runner: InMemoryRunner, request: str):
    """用给定请求运行协调者智能体并委托。"""
    print(f"\n--- 协调者运行请求：'{request}' ---")
    final_result = ""
    try:
        user_id = "user_123"
        session_id = str(uuid.uuid4())
        await runner.session_service.create_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )

        for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(
                role='user',
                parts=[types.Part(text=request)]
            ),
        ):
            if event.is_final_response() and event.content:
                if hasattr(event.content, 'text') and event.content.text:
                    final_result = event.content.text
                elif event.content.parts:
                    text_parts = [part.text for part in event.content.parts if part.text]
                    final_result = "".join(text_parts)
                break

        print(f"协调者最终响应：{final_result}")
        return final_result
    except Exception as e:
        print(f"处理请求时发生错误：{e}")
        return f"处理请求时发生错误：{e}"


async def main():
    """主函数，运行 ADK 示例。"""
    print("--- Google ADK 路由示例（ADK Auto-Flow 风格，DeepSeek via LiteLLM）---")

    runner = InMemoryRunner(coordinator)
    # 示例用法
    result_a = await run_coordinator(runner, "帮我预订巴黎的酒店。")
    print(f"最终输出 A: {result_a}")
    result_b = await run_coordinator(runner, "世界最高的山峰是什么？")
    print(f"最终输出 B: {result_b}")
    result_c = await run_coordinator(runner, "说一个随机的事实。")  # 应委托给 Info
    print(f"最终输出 C: {result_c}")
    result_d = await run_coordinator(runner, "查找下个月飞往东京的航班。")  # 应委托给 Booker
    print(f"最终输出 D: {result_d}")

    # litellm 每次 acompletion 会起后台 LoggingWorker 异步任务，事件循环关闭时
    # 残留任务会导致 “Task was destroyed” 警告 + 退出时 segfault（纯关闭期问题，
    # 不影响结果）。这里结果已全部输出，flush 后直接退出，跳过那段有缺陷的清理。
    import sys as _sys
    _sys.stdout.flush()
    import os as _os
    _os._exit(0)


if __name__ == "__main__":
    import nest_asyncio
    import asyncio
    nest_asyncio.apply()
    asyncio.run(main())
