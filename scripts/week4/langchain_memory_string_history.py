"""
Week 4 · LangChain 1.x 对话记忆（字符串历史版）
==============================================

原课程脚本：OpenAI(completion) + LLMChain + ConversationBufferMemory（LangChain 0.x），
演示旅行顾问跨 3 轮记住用户名字。LangChain 1.3.14 移除了 langchain.chains /
langchain.memory，这里用 LCEL (prompt | llm) + 手动维护字符串历史，等价于
ConversationBufferMemory 的字符串缓冲行为（memory_key="history"）。

适配说明：
  - 无 OPENAI_API_KEY 默认端点 -> 改 DeepSeek（OpenAI 兼容）经 ChatOpenAI 接入。
  - OpenAI(completion LLM, /v1/completions) 在 langchain_openai 1.4.1 + DeepSeek 下
    400（prompt 序列化不兼容），改用 ChatOpenAI（/chat/completions 实测可用）。
    故 completion vs chat 的对比让位于「字符串历史 vs 消息历史」的对比，见
    langchain_memory_message_history.py。
  - http_client trust_env=False：绕开系统代理残留（week1 既有坑，DeepSeek 直连）。
知识块：② Agent 核心机制 · ⑦ Prompt 工程（记忆/多轮）
"""

import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # Windows 中文不乱码（week1 既有坑）

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

import httpx
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

llm = ChatOpenAI(
    temperature=0,
    model=os.environ["DEEPSEEK_MODEL"],
    base_url=os.environ["DEEPSEEK_BASE_URL"],
    api_key=os.environ["DEEPSEEK_API_KEY"],
    http_client=httpx.Client(trust_env=False),
)

template = """你是一名乐于助人的旅行顾问。

之前的对话：
{history}

新问题：{question}
回复："""
prompt = PromptTemplate.from_template(template)
chain = prompt | llm  # LCEL 取代 LLMChain

# 手动字符串历史（替代 ConversationBufferMemory，memory_key="history"）
history = ""
for question in ["我想订机票。", "顺便说一下，我叫 Sam。", "你还记得我的名字吗？"]:
    response = chain.invoke({"history": history, "question": question})
    answer = response.content if hasattr(response, "content") else str(response)
    print(answer)
    history += f"人: {question}\n顾问: {answer}\n"
