"""
Week 4 · LangChain 1.x 对话记忆（消息历史版，对标 return_messages=True）
======================================================================

原课程脚本：ChatOpenAI + ChatPromptTemplate + MessagesPlaceholder +
ConversationBufferMemory(return_messages=True)，演示跨轮记住用户名字。
LangChain 1.3.14 移除了 langchain.memory（ConversationBufferMemory），这里手动维护
消息列表 (List[BaseMessage])，等价于 return_messages=True 的消息缓冲行为。

与 langchain_memory_string_history.py 的对比（核心教学点）：
  - 字符串版：历史拼成一段文本注入 {history}，模型读纯文本上下文。
  - 消息版：历史以 HumanMessage/AIMessage 对象注入 MessagesPlaceholder，
    对齐 chat 模型的多轮消息结构，角色边界更清晰。

适配说明：
  - 无 OPENAI_API_KEY 默认端点 -> 改 DeepSeek（OpenAI 兼容）经 ChatOpenAI 接入。
  - LCEL (prompt | llm) + .invoke({...}) 取代 LLMChain.predict。
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
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_core.messages import HumanMessage, AIMessage

llm = ChatOpenAI(
    temperature=0,
    model=os.environ["DEEPSEEK_MODEL"],
    base_url=os.environ["DEEPSEEK_BASE_URL"],
    api_key=os.environ["DEEPSEEK_API_KEY"],
    http_client=httpx.Client(trust_env=False),
)

prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template("你是一名友好的助手。"),
    MessagesPlaceholder(variable_name="chat_history"),
    HumanMessagePromptTemplate.from_template("{question}"),
])
chain = prompt | llm  # LCEL 取代 LLMChain

# 手动消息历史（替代 ConversationBufferMemory(return_messages=True)）
chat_history = []
for question in ["你好，我是 Jane。", "你还记得我的名字吗？"]:
    response = chain.invoke({"chat_history": chat_history, "question": question})
    answer = response.content
    print(answer)
    chat_history.append(HumanMessage(content=question))
    chat_history.append(AIMessage(content=answer))
