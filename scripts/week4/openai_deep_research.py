"""
Week 4 · OpenAI Deep Research API（responses + 推理摘要 + 联网搜索 + 引用）
==========================================================================

演示 OpenAI 的 Deep Research 接口：
  - client.responses.create 调用 o3-deep-research 模型
  - reasoning={"summary":"auto"}：返回模型内部推理摘要
  - tools=[{"type":"web_search_preview"}]：托管联网搜索工具
  - 产出长报告 + 内嵌引用（annotations，含被引用文本/标题/URL/位置）
  - 检查中间步骤：reasoning / web_search_call / code_interpreter_call

⚠️ 平台限制（本机不可跑）：
  此脚本依赖 OpenAI 平台独有能力——/responses API、o3-deep-research-2025-06-26
  模型、web_search_preview 托管工具。DeepSeek / 豆包仅兼容 /chat/completions，
  没有 /responses 端点、没有该模型、没有该工具，无法替代。运行需真实的 OpenAI
  API key 且账号具备 Deep Research 访问权限。脚本顶部有占位符守卫，未配置真实
  key 时直接提示并退出，避免空跑昂贵的 deep research 调用。

原版：Marco Fago 教程，api_key 硬编码占位符；此处改为从 .env 读取。
知识块：④ 深度研究 · ⑥ 工具使用
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# 加载 agent-training 根目录的 .env
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# --- 占位符守卫：未配置真实 OpenAI key 时直接退出，避免空跑昂贵的 deep research 调用 ---
_api_key = os.environ.get("OPENAI_API_KEY", "")
if not _api_key or _api_key.startswith("sk-your") or _api_key == "YOUR_OPENAI_API_KEY":
    print("⚠️ 未配置真实 OpenAI API key（.env 里是占位符 sk-your-openai-api-key）。")
    print("Deep Research 需要真实的 OpenAI API key，且账号有 Deep Research 访问权限。")
    print("DeepSeek/豆包无法替代：它们没有 /responses API、没有 o3-deep-research 模型、没有 web_search_preview 工具。")
    sys.exit(0)

# 用你的 API 密钥初始化客户端
client = OpenAI(api_key=_api_key)

# 定义智能体角色和用户研究问题
system_message = """你是一名专业研究员，需撰写结构化、数据驱动的报告。
关注数据洞见，使用可靠来源，并在正文中插入引用。"""
user_query = "研究司美格鲁肽对全球医疗体系的经济影响。"

# 创建 Deep Research API 调用
response = client.responses.create(
    model="o3-deep-research-2025-06-26",
    input=[
        {
            "role": "developer",
            "content": [{"type": "input_text", "text": system_message}]
        },
        {
            "role": "user",
            "content": [{"type": "input_text", "text": user_query}]
        }
    ],
    reasoning={"summary": "auto"},
    tools=[{"type": "web_search_preview"}]
)

# 获取并打印最终报告
final_report = response.output[-1].content[0].text
print(final_report)

# --- 获取内嵌引用和元数据 ---
print("--- 引用 ---")
annotations = response.output[-1].content[0].annotations

if not annotations:
    print("报告中未发现引用。")
else:
    for i, citation in enumerate(annotations):
        # 被引用的文本片段
        cited_text = final_report[citation.start_index:citation.end_index]

        print(f"引用 {i+1}:")
        print(f"  被引用文本：{cited_text}")
        print(f"  标题：{citation.title}")
        print(f"  链接：{citation.url}")
        print(f"  位置：字符 {citation.start_index}–{citation.end_index}")
print("\n" + "=" * 50 + "\n")

# --- 检查中间步骤 ---
print("--- 中间步骤 ---")

# 1. 推理步骤：模型生成的内部计划和摘要
try:
    reasoning_step = next(item for item in response.output if item.type == "reasoning")
    print("\n[发现推理步骤]")
    for summary_part in reasoning_step.summary:
        print(f"  - {summary_part.text}")
except StopIteration:
    print("\n未发现推理步骤。")

# 2. 网络搜索调用：智能体实际执行的搜索查询
try:
    search_step = next(item for item in response.output if item.type == "web_search_call")
    print("\n[发现网络搜索调用]")
    print(f"  执行查询：'{search_step.action['query']}'")
    print(f"  状态：{search_step.status}")
except StopIteration:
    print("\n未发现网络搜索步骤。")

# 3. 代码执行：智能体使用代码解释器运行的代码
try:
    code_step = next(item for item in response.output if item.type == "code_interpreter_call")
    print("\n[发现代码执行步骤]")
    print("  输入代码：")
    print(f"  ```python\n{code_step.input}\n  ```")
    print("  输出结果：")
    print(f"  {code_step.output}")
except StopIteration:
    print("\n未发现代码执行步骤。")
