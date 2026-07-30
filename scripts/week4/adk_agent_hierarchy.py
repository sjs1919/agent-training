"""
Week 4 · Google ADK 自定义 BaseAgent + Agent 层级关系
====================================================

演示 ADK 的两类 Agent 组合：
  1. LlmAgent        - 由 LLM 驱动的 Agent（Greeter / Coordinator）
  2. 自定义 BaseAgent - 重写 _run_async_impl 实现非 LLM 行为（TaskExecutor）

核心知识点：
  1. LlmAgent(sub_agents=[...]) 声明父子层级，ADK 自动建立 parent_agent 关系
  2. 自定义 BaseAgent 必须实现 _run_async_impl(ctx) -> AsyncGenerator[Event, None]
  3. parent_agent / sub_agents 是双向关系，构造后即可断言
  4. 本脚本只验证层级构造，不跑 Runner、不调 LLM，
     故 model="gemini-2.0-flash-exp" 仅为字段赋值，不会发起任何 API 请求，
     无需 Gemini key。

知识块：⑧ Agent 集群 · ② Agent 核心机制
"""

import os
import sys
from pathlib import Path

# Windows stdout 默认 GBK，输出中文会乱码，强制 UTF-8（week1 既有坑）。
sys.stdout.reconfigure(encoding="utf-8")

# 环境前置：google.adk 导入链可能触发 litellm，按 week4 既有约定预防 import 卡死。
# 本脚本不发网络请求，故不设代理；仅关遥测 + 用本地成本表 + 本地 tiktoken 词表。
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("LITELLM_TELEMETRY", "False")
os.environ.setdefault(
    "CUSTOM_TIKTOKEN_CACHE_DIR", str(Path.home() / ".cache" / "tiktoken")
)

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from typing import AsyncGenerator


class TaskExecutor(BaseAgent):
    """自定义非 LLM 行为 Agent。"""
    name: str = "TaskExecutor"
    description: str = "执行预定义任务。"

    async def _run_async_impl(self, context: InvocationContext) -> AsyncGenerator[Event, None]:
         yield Event(author=self.name, content="任务成功完成。")

greeter = LlmAgent(
    name="Greeter",
    model="gemini-2.0-flash-exp",
    instruction="你是一名友好的问候者。"
)
task_doer = TaskExecutor()

coordinator = LlmAgent(
    name="Coordinator",
    model="gemini-2.0-flash-exp",
    description="协调问候与任务执行。",
    instruction="问候时委托 Greeter，执行任务时委托 TaskExecutor。",
    sub_agents=[
         greeter,
         task_doer
    ]
)

assert greeter.parent_agent == coordinator
assert task_doer.parent_agent == coordinator

print("Agent 层级关系创建成功。")
