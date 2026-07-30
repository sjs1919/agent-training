"""
Week 4 · 工具调用 Agent / create_agent + LangGraph 工具循环
==========================================================

用 LangChain 1.x 的 create_agent 构造一个能调用工具的 Agent：
  - search_information：模拟检索工具，按预设词表返回事实
  - create_agent 返回一个 CompiledStateGraph，内部自动跑
    「LLM 决策 -> 调工具 -> 观察结果 -> 再决策」循环，直到产出最终回复
  - asyncio.gather 并发跑 3 个查询（含一个触发默认回复的兜底用例）

核心知识点：
  1. @tool 装饰器把普通函数注册成 LangChain 工具（docstring 作为调用说明）
  2. create_agent：让模型用原生 function-calling 能力选工具，内部用 LangGraph 驱动循环
  3. ainvoke({"messages": [...]})：消息列表作为输入，末条 AIMessage 即最终回复
  4. asyncio.gather + ainvoke：并发分发多个 Agent 任务

说明：原版用 ChatGoogleGenerativeAI(gemini-2.0-flash) + getpass 交互输入 key，
并使用 0.x 旧 API（create_tool_calling_agent + AgentExecutor）。本机装的是
langchain 1.3.14，旧 API 已移除，故改用 1.x 的 create_agent；同时无 Gemini key
且非交互环境，故改用主用豆包（OpenAI 兼容），失败自动 fallback 到 DeepSeek，
API key 从 .env 读取。工具调用/并发逻辑等价保留。
知识块：② Agent 核心机制 · ⑥ 工具使用
"""

import asyncio
import os
import sys
from pathlib import Path

import nest_asyncio
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool as langchain_tool
from langchain_openai import ChatOpenAI

# 加载 agent-training 根目录的 .env
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# --- 配置 ---
# 主用火山豆包（OpenAI 兼容），失败自动 fallback 到 DeepSeek
PROVIDERS = ("volc", "deepseek")


def build_llm(provider: str) -> ChatOpenAI:
    """按 provider 名字构造一个 OpenAI 兼容的 ChatOpenAI。"""
    if provider == "volc":
        return ChatOpenAI(
            model=os.environ["VOLC_MODEL"],
            api_key=os.environ["VOLC_API_KEY"],
            base_url=os.environ["VOLC_BASE_URL"],
            temperature=0,
        )
    return ChatOpenAI(
        model=os.environ["DEEPSEEK_MODEL"],
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=os.environ["DEEPSEEK_BASE_URL"],
        temperature=0,
    )


# --- 定义工具 ---
@langchain_tool
def search_information(query: str) -> str:
    """
    根据主题提供事实信息。用于回答如“法国首都”或“伦敦天气？”等问题。
    """
    print(f"\n--- 🛠️ 工具调用：search_information, 查询：'{query}' ---")
    # 用预设结果模拟搜索工具
    simulated_results = {
        "weather in london": "伦敦当前天气多云，气温 15°C。",
        "capital of france": "法国的首都是巴黎。",
        "population of earth": "地球人口约 80 亿。",
        "tallest mountain": "珠穆朗玛峰是海拔最高的山峰。",
        "default": f"模拟搜索 '{query}'：未找到具体信息，但该主题很有趣。"
    }
    result = simulated_results.get(query.lower(), simulated_results["default"])
    print(f"--- 工具结果：{result} ---")
    return result


tools = [search_information]

SYSTEM_PROMPT = "你是一个乐于助人的助手。"


def build_agent(provider: str):
    """用指定 provider 构造工具调用 Agent（返回 CompiledStateGraph）。"""
    llm = build_llm(provider)
    return create_agent(model=llm, tools=tools, system_prompt=SYSTEM_PROMPT)


async def run_agent_with_tool(agent, query: str):
    """用 Agent 执行查询并打印最终回复。"""
    print(f"\n--- 🏃 Agent 运行查询：'{query}' ---")
    response = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})
    final = response["messages"][-1].content
    print("\n--- ✅ Agent 最终回复 ---")
    print(final)


async def main(agent):
    """并发运行多个 Agent 查询。"""
    tasks = [
        run_agent_with_tool(agent, "What is the capital of France?"),
        run_agent_with_tool(agent, "What's the weather like in London?"),
        run_agent_with_tool(agent, "Tell me something about dogs."),  # 触发默认工具回复
    ]
    await asyncio.gather(*tasks)


def run():
    last_err = None
    nest_asyncio.apply()
    for provider in PROVIDERS:
        try:
            agent = build_agent(provider)
            print(f"✅ 语言模型已初始化 [provider={provider}]")
            asyncio.run(main(agent))
            # httpx/asyncio 关闭期偶发 segfault（exit 139），结果已全部打印，直接干净退出
            sys.stdout.flush()
            os._exit(0)
        except Exception as e:
            print(f"[provider={provider}] 失败: {e}")
            last_err = e

    print(f"\n所有 provider 均失败: {last_err}")


if __name__ == "__main__":
    run()
