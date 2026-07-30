"""
Week 4 · ADK Vertex AI Search 检索增强 Agent
============================================

用 Google ADK 的 VertexAiSearchTool 做检索增强问答：
  - data_store_id 指向一个 Vertex AI Search 数据仓库（已索引的战略文档等）
  - LlmAgent 挂载 VertexAiSearchTool，自动检索 datastore 后生成带来源归因的回答
  - 流式打印增量文本 + 最终的来源归因数量

⚠️ 平台限制（本机不可跑）：
  此脚本依赖 Google Cloud 基础设施--需要一个 GCP 项目、一个已建好的 Vertex AI
  Search datastore（DATASTORE_ID）、以及具备 Vertex AI Search 访问权限的服务账号
  （应用默认凭据 ADC）。同时 VertexAiSearchTool 要求 Gemini 模型（走 Gemini 的
  grounding 检索），本机无 GCP 配置、无 Gemini key，故脚本仅在未设置 DATASTORE_ID
  时提示并退出。DeepSeek/豆包无法替代。

  注：原版教程用 agents.VSearchAgent，该类在 ADK 2.5.0 已移除，新版用
  LlmAgent + VertexAiSearchTool(data_store_id=...) 等效替代（本脚本已迁移）。
知识块：③ RAG / 检索增强 · ④ 深度研究
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.adk.tools import VertexAiSearchTool  # noqa: E402
from google.genai import types  # noqa: E402

DATASTORE_ID = os.environ.get("DATASTORE_ID")
APP_NAME = "vsearch_app"
USER_ID = "user_123"
SESSION_ID = "session_456"

vsearch_agent = LlmAgent(
    name="q2_strategy_vsearch_agent",
    description="用 Vertex AI Search 回答 Q2 战略文档相关问题。",
    model="gemini-2.0-flash-exp",
    tools=[VertexAiSearchTool(data_store_id=DATASTORE_ID)] if DATASTORE_ID else [],
    instruction="根据 Vertex AI Search 检索到的内容回答用户问题，并引用来源。",
)

runner = Runner(
    agent=vsearch_agent,
    app_name=APP_NAME,
    session_service=InMemorySessionService(),
)


async def call_vsearch_agent_async(query: str):
    print(f"用户：{query}")
    print("Agent:", end="", flush=True)

    try:
        content = types.Content(role='user', parts=[types.Part(text=query)])
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=content
        ):
            if hasattr(event, 'content_part_delta') and event.content_part_delta:
                print(event.content_part_delta.text, end="", flush=True)
            if event.is_final_response():
                print()
                if event.grounding_metadata:
                    print(f"（来源归因：{len(event.grounding_metadata.grounding_attributions)} 个来源）")
                else:
                    print("（未找到来源元数据）")
                print("-" * 30)

    except Exception as e:
        print(f"\n出错：{e}")
        print("请检查 datastore ID 是否正确及服务账号权限。")
        print("-" * 30)


async def run_vsearch_example():
    await call_vsearch_agent_async("总结 Q2 战略文档的要点。")
    await call_vsearch_agent_async("实验室 X 的安全流程有哪些？")


if __name__ == "__main__":
    if not DATASTORE_ID:
        print("错误：未设置 DATASTORE_ID 环境变量。")
        print("此脚本还需 GCP 项目 + Vertex AI Search datastore + 服务账号 + Gemini 访问权限，本机不具备。")
    else:
        try:
            asyncio.run(run_vsearch_example())
        except RuntimeError as e:
            if "cannot be called from a running event loop" in str(e):
                print("事件循环环境下跳过执行，请直接运行脚本。")
            else:
                raise e
