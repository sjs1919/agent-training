"""
Week 4 · 补缺 - 协调者路由 / RunnableBranch 多 Agent 委托
=========================================================

用 LangChain 的 RunnableBranch 模拟 ADK 的「协调者 + 子智能体」自动流转：
  协调者链：把用户请求分类成 booker / info / unclear（只输出一个词）
  委托分支：按分类结果把请求转给对应的子处理器
    - booker  -> booking_handler  （模拟预订）
    - info    -> info_handler      （模拟信息检索）
    - unclear -> unclear_handler   （兜底，要求补充说明）

核心知识点：
  1. ChatPromptTemplate.from_messages 构造带 system/user 的路由提示
  2. RunnablePassthrough.assign 在不丢原入参的前提下追加字段
  3. RunnableBranch 按条件选择分支执行（等价于 if/elif/else 的链式写法）
  4. dict | branch | lambda 组合：先并行算 decision 与原样透传 request，
     再走分支，最后取出 output

说明：原版用 ChatGoogleGenerativeAI(gemini-2.5-flash)，本仓库未配置
GOOGLE_API_KEY 且未装 langchain-google-genai，故改用主用豆包（OpenAI 兼容）。
路由/委托逻辑完全保留，LLM 类不影响演示效果。
知识块：⑧ Agent 集群 · ② Agent 核心机制
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableBranch, RunnablePassthrough
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


# --- 定义模拟子智能体处理器（等同于 ADK sub_agents） ---


def booking_handler(request: str) -> str:
    """模拟预订智能体处理请求。"""
    print("\n--- 委托给预订处理器 ---")
    return f"预订处理器已处理请求：'{request}'。结果：模拟预订动作。"


def info_handler(request: str) -> str:
    """模拟信息智能体处理请求。"""
    print("\n--- 委托给信息处理器 ---")
    return f"信息处理器已处理请求：'{request}'。结果：模拟信息检索。"


def unclear_handler(request: str) -> str:
    """处理无法委托的请求。"""
    print("\n--- 处理不明确请求 ---")
    return f"协调者无法委托请求：'{request}'。请补充说明。"


# --- 定义协调者路由链（等同于 ADK 协调者指令） ---
coordinator_router_prompt = ChatPromptTemplate.from_messages([
    ("system", """分析用户请求，判断应由哪个专属处理器处理。
    - 若请求涉及预订机票或酒店，输出 'booker'。
    - 其他一般信息问题，输出 'info'。
    - 若请求不明确或不属于上述类别，输出 'unclear'。
    只输出一个词：'booker'、'info' 或 'unclear'。"""),
    ("user", "{request}")
])


def build_coordinator_agent(provider: str):
    """用指定 provider 构造协调者 Agent：路由链 + 委托分支。"""
    llm = build_llm(provider)
    coordinator_router_chain = coordinator_router_prompt | llm | StrOutputParser()

    # --- 定义委托逻辑（等同于 ADK 的 Auto-Flow） ---
    branches = {
        "booker": RunnablePassthrough.assign(output=lambda x: booking_handler(x['request']['request'])),
        "info": RunnablePassthrough.assign(output=lambda x: info_handler(x['request']['request'])),
        "unclear": RunnablePassthrough.assign(output=lambda x: unclear_handler(x['request']['request'])),
    }

    delegation_branch = RunnableBranch(
        (lambda x: x['decision'].strip() == 'booker', branches["booker"]),
        (lambda x: x['decision'].strip() == 'info', branches["info"]),
        branches["unclear"]  # 默认分支
    )

    return (
        {
            "decision": coordinator_router_chain,
            "request": RunnablePassthrough(),
        }
        | delegation_branch
        | (lambda x: x['output'])
    )


# --- 示例用法 ---
def run_examples(agent):
    print("--- 预订请求示例 ---")
    request_a = "帮我预订飞往伦敦的机票。"
    result_a = agent.invoke({"request": request_a})
    print(f"最终结果 A: {result_a}")

    print("\n--- 信息请求示例 ---")
    request_b = "意大利的首都是哪里？"
    result_b = agent.invoke({"request": request_b})
    print(f"最终结果 B: {result_b}")

    print("\n--- 不明确请求示例 ---")
    request_c = "讲讲量子物理。"
    result_c = agent.invoke({"request": request_c})
    print(f"最终结果 C: {result_c}")


def main():
    last_err = None
    for provider in PROVIDERS:
        try:
            llm = build_llm(provider)
            print(f"语言模型初始化成功：{llm.model} [provider={provider}]")
            agent = build_coordinator_agent(provider)
            run_examples(agent)
            return
        except Exception as e:
            print(f"[provider={provider}] 失败: {e}")
            last_err = e

    print(f"\n所有 provider 均失败: {last_err}")


if __name__ == "__main__":
    main()
