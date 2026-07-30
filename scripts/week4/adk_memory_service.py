"""
Week 4 · Google ADK 长期记忆服务（跨会话记忆）
=============================================

原课程脚本用 VertexAiMemoryBankService（GCP Vertex AI 托管），需要 GCP project +
认证 + 已部署的 Agent Engine，本机不可跑（见 [[project-agent-training-litellm-adk-env]]
「需 GCP，本机不可跑，仅归档」）。原片段：

    from google.adk.memory import VertexAiMemoryBankService
    memory_service = VertexAiMemoryBankService(
        project="PROJECT_ID", location="LOCATION",
        agent_engine_id=agent_engine.api_resource.name.split("/")[-1])
    session = await session_service.get_session(app_name=..., user_id="USER_ID", session_id=session.id)
    await memory_service.add_session_to_memory(session)

本文件改用 InMemoryMemoryService（同实现 BaseMemoryService 接口，本地可跑）演示
同一概念：把一个 session 的事件写入长期记忆，再用「另一个新 session」通过
search_memory 跨会话检索命中 -- 即跨会话的长期记忆（对照 langchain_memory_*.py
的「会话内缓冲记忆」）。

核心 API：
  - memory_service.add_session_to_memory(session)   写入
  - memory_service.search_memory(*, app_name, user_id, query)  跨会话检索
本 demo 不调 LLM、不发网络请求，纯本地。
知识块：② Agent 核心机制（记忆）· ⑧ Agent 集群
"""

import asyncio
import sys
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # Windows 中文不乱码（week1 既有坑）

# 环境前置：google.adk 导入链可能触发 litellm，按 week4 既有约定预防 import 卡死。
os_env = __import__("os").environ
os_env.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os_env.setdefault("LITELLM_TELEMETRY", "False")
os_env.setdefault("CUSTOM_TIKTOKEN_CACHE_DIR", str(Path.home() / ".cache" / "tiktoken"))

from google.genai import types
from google.adk.events import Event
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService


def make_event(author: str, text: str, role: str) -> Event:
    """构造一条带文本 content 的事件。"""
    return Event(
        id=str(uuid.uuid4()),
        author=author,
        content=types.Content(parts=[types.Part(text=text)], role=role),
    )


def content_text(content) -> str:
    """从 Content（或字符串）提取纯文本，兼容两种返回。"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts = getattr(content, "parts", None) or []
    return "".join(getattr(p, "text", "") or "" for p in parts)


async def main():
    app_name = "travel_app"
    user_id = "sam"
    memory_service = InMemoryMemoryService()  # 本地等价 VertexAiMemoryBankService
    session_service = InMemorySessionService()

    # 注意：InMemoryMemoryService.search_memory 用关键字匹配（re \w+ 分词后精确等值），
    # 中文无词边界、整句会被当成单个 token 导致自然提问匹配不上；GCP 的
    # VertexAiMemoryBankService 才做真语义检索。这里用英文内容让关键字命中可复现。
    # --- Session 1：用户透露偏好 ---
    session1 = await session_service.create_session(app_name=app_name, user_id=user_id)
    await session_service.append_event(
        session1, make_event("user", "I'm planning a trip next month. I prefer beach cities.", "user")
    )
    await session_service.append_event(
        session1, make_event("travel_bot", "Got it, you like beach cities. Any specific destination?", "model")
    )
    # 把 session1 写入长期记忆（对标 VertexAiMemoryBankService.add_session_to_memory）
    await memory_service.add_session_to_memory(session1)
    print(f"[session1 id={session1.id}] 已写入长期记忆。")

    # --- Session 2：全新会话，与 session1 互不共享 buffer ---
    session2 = await session_service.create_session(app_name=app_name, user_id=user_id)
    print(f"[session2 id={session2.id}] 新会话（与 session1 隔离，buffer 不共享）。")

    # 跨会话检索长期记忆（query 关键字 beach 命中 session1 的事件）
    resp = await memory_service.search_memory(
        app_name=app_name, user_id=user_id, query="beach"
    )
    print(f"\nsearch_memory(query='beach') 命中 {len(resp.memories)} 条记忆：")
    for i, mem in enumerate(resp.memories):
        print(f"  [{i}] author={mem.author} | content={content_text(mem.content)!r}")


if __name__ == "__main__":
    asyncio.run(main())
