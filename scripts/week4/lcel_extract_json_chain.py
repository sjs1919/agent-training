"""
Week 4 · 补缺 - LangChain LCEL 链式调用入门
=============================================

用 LCEL（LangChain Expression Language）把两个 prompt 串成一条链：
  提取链：原始文本 -> 提取技术规格
  转换链：技术规格 -> 结构化 JSON（cpu / memory / storage）

核心知识点：
  1. ChatPromptTemplate.from_template 构造提示模板
  2. `|` 运算符把 prompt | llm | parser 组成链
  3. StrOutputParser 把 LLM 的 AIMessage 转成纯字符串
  4. 全链用 dict 把上一条链的输出喂给下一条链的变量（specifications）

对比单次调用：
  单次：一次 prompt 进、一次结果出
  链式：上一步输出自动作为下一步输入，无需手动传递

Provider：主用火山豆包（ark-code-latest），失败自动 fallback 到 DeepSeek。
知识块：① API 与 Prompt · ② LCEL 链式编排
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# 加载 agent-training 根目录的 .env
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


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


# --- 提示 1：信息提取 ---
prompt_extract = ChatPromptTemplate.from_template(
    "请从以下文本中提取技术规格：\n\n{text_input}"
)

# --- 提示 2：转为 JSON ---
prompt_transform = ChatPromptTemplate.from_template(
    "请将以下技术规格转为 JSON 格式，包含 'cpu'、'memory' 和 'storage' 三个键：\n\n{specifications}"
)

# --- 待处理文本 ---
input_text = "新款笔记本配备 3.5GHz 八核处理器、16GB 内存和 1TB NVMe SSD。"

# --- 主备 Provider 逐个尝试，第一个成功即返回 ---
last_err = None
for provider in ("volc", "deepseek"):
    llm = build_llm(provider)

    # 提取链：prompt -> llm -> 字符串
    extraction_chain = prompt_extract | llm | StrOutputParser()

    # 全链：把提取链的输出作为 'specifications' 喂给转换链
    full_chain = (
        {"specifications": extraction_chain}
        | prompt_transform
        | llm
        | StrOutputParser()
    )

    try:
        final_result = full_chain.invoke({"text_input": input_text})
        print(f"\n[provider={provider}] --- 最终 JSON 输出 ---")
        print(final_result)
        sys.exit(0)
    except Exception as e:
        print(f"[provider={provider}] 失败: {e}", file=sys.stderr)
        last_err = e

sys.exit(f"所有 provider 均失败: {last_err}")
