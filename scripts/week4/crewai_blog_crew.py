"""
Week 4 · CrewAI 内容创作 AI 团队（研究 + 写作 sequential 流程）
==============================================================

用 CrewAI 的 Agent / Task / Crew 编排一个两角色团队：
  researcher -> 查找 AI 趋势；writer -> 据研究结果写博客。
  Process.sequential 顺序执行，writing_task.context=[research_task] 拿前序结果。

适配说明（原版用 Gemini 2.0 Flash，本仓库无 GOOGLE_API_KEY）：
  改用 DeepSeek（OpenAI 兼容）经 crewai 原生 LLM 类（litellm 封装）接入。
  - crewai 1.15.9 的 Agent.llm 只收 str | crewai BaseLLM，不收 LangChain
    ChatOpenAI（BaseChatModel）；故原版 Crew(llm=ChatGoogleGenerativeAI) 写法在此
    版本已失效，改为 crewai.LLM(model="openai/"+model, base_url=, api_key=)。
  - litellm 经 DeepSeek 国内端点直连，无需代理（trust_env 默认即可，实测直连 200）。
  - Crew(verbose=2) 在 pydantic v2 bool 字段下会校验失败，改 verbose=True。
环境前置（crewai 内部 import litellm，按 week4 既有约定预防 import 卡死）：
  - LITELLM_LOCAL_MODEL_COST_MAP=True / LITELLM_TELEMETRY=False
  - CUSTOM_TIKTOKEN_CACHE_DIR 指向本地 tiktoken 词表缓存
知识块：⑧ Agent 集群 · ② Agent 核心机制
"""

import os
import sys
from pathlib import Path

# Windows stdout 默认 GBK，输出中文会乱码，强制 UTF-8（week1 既有坑）。
sys.stdout.reconfigure(encoding="utf-8")

# 环境前置：必须在 import crewai（它 import litellm）之前生效。
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("LITELLM_TELEMETRY", "False")
os.environ.setdefault(
    "CUSTOM_TIKTOKEN_CACHE_DIR", str(Path.home() / ".cache" / "tiktoken")
)

from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM

# .env 在项目根（projects/agent-training/.env），脚本在 scripts/week4/ 下，向上三级。
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


def setup_environment():
    """加载环境变量并检查 API 密钥。"""
    if not os.getenv("DEEPSEEK_API_KEY"):
        raise ValueError("DEEPSEEK_API_KEY 未设置，请在 .env 文件中配置。")


def build_llm() -> LLM:
    """DeepSeek 经 OpenAI 兼容端点接入（crewai LLM = litellm 封装，直连）。"""
    return LLM(
        model="openai/" + os.environ["DEEPSEEK_MODEL"],
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=os.environ["DEEPSEEK_BASE_URL"],
    )


def main():
    """
    初始化并运行内容创作 AI 团队，使用 DeepSeek 模型。
    """
    setup_environment()

    # 指定语言模型（crewai 1.15.9：llm 传给 Agent，不传给 Crew）
    llm = build_llm()

    # 定义 Agent 角色与目标
    researcher = Agent(
        role='高级研究分析师',
        goal='查找并总结 AI 最新趋势。',
        backstory="你是一名经验丰富的研究分析师，擅长发现关键趋势并整合信息。",
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )

    writer = Agent(
        role='技术内容写作者',
        goal='根据研究结果撰写清晰易懂的博客。',
        backstory="你是一名技术写作高手，能将复杂技术转化为通俗内容。",
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )

    # 定义任务
    research_task = Task(
        description="调研 2024-2025 年 AI 三大新兴趋势，关注实际应用与影响。",
        expected_output="详细总结三大 AI 趋势，包括要点与来源。",
        agent=researcher,
    )

    writing_task = Task(
        description="根据研究结果撰写一篇 500 字博客，内容通俗易懂。",
        expected_output="完整的 500 字 AI 趋势博客。",
        agent=writer,
        context=[research_task],
    )

    # 创建团队
    blog_creation_crew = Crew(
        agents=[researcher, writer],
        tasks=[research_task, writing_task],
        process=Process.sequential,
        verbose=True,
    )

    # 执行团队任务
    print("## 使用 DeepSeek 运行博客创作团队... ##")
    try:
        result = blog_creation_crew.kickoff()
        print("\n------------------\n")
        print("## 团队最终输出 ##")
        print(result)
    except Exception as e:
        print(f"\n发生异常：{e}")


if __name__ == "__main__":
    main()
