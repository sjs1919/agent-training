"""
第一周 · Day 2 — Function Calling / Tool Use 实战
==================================================
目标：在 Day 1 主备架构上叠加工具调用，跑通 Agent 闭环：
      用户提问 → 模型决定调哪个工具 → 代码执行工具 → 结果返回模型 → 模型组织语言回答

核心认知：Tool Use 是 Agent 的"手"——没有工具，Agent 只能聊天不能干活。
        学会了 Function Calling = Agent 开发入门，后续 MCP/LangGraph 都是在这一层上叠加。

今日工具：query_orders() —— 查询 3D 打印/CNC 加工订单（scripts/week1/data/orders.csv，30条）

[AI:Claude] 架构设计：主备 fallback + Function Calling Agent 循环
"""

import csv
import json
import os
import sys
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from openai import OpenAI
import httpx

# Windows 默认 stdout 走 GBK，编码不了 emoji/部分中文 -> 切 UTF-8（开箱即跑）
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent.parent / ".env")

# ============================================================
# Provider 注册表（沿用 Day 1 主备架构）
# ============================================================

PROVIDERS = [
    {
        "name": "火山豆包(coding)",
        "enabled": True,
        "api_key": os.getenv("VOLC_API_KEY", ""),
        "base_url": os.getenv("VOLC_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding/v3"),
        "model": os.getenv("VOLC_MODEL", "ark-code-latest"),
        "note": "主用 · 字节编程套餐",
    },
    {
        "name": "DeepSeek",
        "enabled": True,
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "note": "备用1 · ¥1/百万Token",
    },
    {
        "name": "Kimi(coding)",
        "enabled": os.getenv("KIMI_ENABLED", "false").lower() == "true",
        "api_key": os.getenv("KIMI_API_KEY", ""),
        "base_url": os.getenv("KIMI_BASE_URL", "https://api.kimi.com/coding/v1"),
        "model": os.getenv("KIMI_MODEL", "kimi-for-coding"),
        "note": "备用2 · 会员过期暂禁用",
    },
]


def _is_real_key(key: str) -> bool:
    return bool(key) and "your-" not in key.lower()


# ============================================================
# 工具定义（OpenAI Function Calling 格式）
# 导航：阅读导航_week1_week2.md → Week1 Day2 → "OpenAI Function Calling 协议"
# 知识：Tool definition = name + description + parameters(JSON Schema)
#       name/description 是模型判断"该不该调这个工具"的唯一依据，必须精确
# ============================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_orders",
            "description": (
                "查询 3D 打印/CNC 加工订单列表。"
                "可按客户名、状态、加工环节、交期范围筛选，支持排序。"
                "返回 JSON 数组，每个订单包含：id、客户名、产品、数量、交期、当前环节、状态。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer": {
                        "type": "string",
                        "description": "按客户名模糊筛选，如'深圳精密五金'、'东莞模具厂'",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["生产中", "待排产", "即将超期", "已完成"],
                        "description": "按订单状态精确筛选",
                    },
                    "stage": {
                        "type": "string",
                        "description": "按当前加工环节筛选，如'CNC加工'、'质检'、'备料'、'热处理'、'表面处理'、'焊接'、'包装'",
                    },
                    "due_before": {
                        "type": "string",
                        "description": "交期在此日期之前（含当天），格式 YYYY-MM-DD",
                    },
                    "due_after": {
                        "type": "string",
                        "description": "交期在此日期之后（含当天），格式 YYYY-MM-DD",
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["交期", "数量", "id"],
                        "description": "排序字段，默认不排序",
                    },
                    "sort_order": {
                        "type": "string",
                        "enum": ["asc", "desc"],
                        "description": "升序(asc)或降序(desc)，默认升序",
                    },
                },
                "required": [],
            },
        },
    }
]

# ============================================================
# 工具实现：query_orders()
# ============================================================

ORDERS_CACHE = None  # 只读一次 CSV


def _load_orders():
    global ORDERS_CACHE
    if ORDERS_CACHE is None:
        csv_path = Path(__file__).parent / "data" / "orders.csv"
        with open(csv_path, encoding="utf-8") as f:
            ORDERS_CACHE = list[dict[str | Any, str | Any]](csv.DictReader(f))
    return ORDERS_CACHE


def query_orders(
    customer=None,
    status=None,
    stage=None,
    due_before=None,
    due_after=None,
    sort_by=None,
    sort_order="asc",
):
    """查询订单，返回筛选 + 排序后的结果列表"""
    orders = _load_orders()
    result = []

    for o in orders:
        # 客户名模糊匹配
        if customer and customer not in o["客户名"]:
            continue
        # 状态精确匹配
        if status and o["状态"] != status:
            continue
        # 环节精确匹配
        if stage and o["当前环节"] != stage:
            continue
        # 交期范围
        if due_before and o["交期"] > due_before:
            continue
        if due_after and o["交期"] < due_after:
            continue
        result.append(o)

    # 排序
    if sort_by:
        key_map = {"交期": "交期", "数量": "数量", "id": "id"}
        key = key_map.get(sort_by, "交期")
        reverse = sort_order == "desc"
        if key == "数量":
            result.sort(key=lambda x: int(x[key]), reverse=reverse)
        else:
            result.sort(key=lambda x: x[key], reverse=reverse)

    return {
        "total": len(result),
        "orders": result,
    }


def execute_tool(tool_name: str, arguments: dict) -> dict:
    """工具调度器：根据 tool_name 分发到具体实现"""
    if tool_name == "query_orders":
        return query_orders(**arguments)
    return {"error": f"未知工具: {tool_name}"}


# ============================================================
# API 调用（扩展 Day 1，增加 tools 支持）
# ============================================================

def call_llm(provider, messages, tools=None, max_tokens=1024, temperature=0.3):
    """用指定 provider 调用一次 LLM（支持 tools 参数）"""
    if not provider.get("enabled"):
        raise RuntimeError(f"provider {provider['name']} 已禁用")
    if not _is_real_key(provider["api_key"]):
        raise RuntimeError(f"provider {provider['name']} key 未配置")

    client = OpenAI(
        api_key=provider["api_key"],
        base_url=provider["base_url"],
        http_client=httpx.Client(trust_env=False),  # 绕过系统/注册表代理直连
    )
    kwargs = dict(
        model=provider["model"],
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if tools:
        kwargs["tools"] = tools
    response = client.chat.completions.create(**kwargs)
    return response, provider


def call_with_fallback(messages, tools=None, max_tokens=1024, temperature=0.3):
    """主备 fallback（Day 1 增强版 —— 支持 tools 参数）"""
    log = []
    last_err = None
    for p in PROVIDERS:
        if not p.get("enabled"):
            log.append(f"  ⏭️  {p['name']:18s} 跳过（已禁用）")
            continue
        if not _is_real_key(p["api_key"]):
            log.append(f"  ⏭️  {p['name']:18s} 跳过（key 未配置）")
            continue
        try:
            resp, used = call_llm(p, messages, tools=tools, max_tokens=max_tokens, temperature=temperature)
            log.append(f"  ✅  {p['name']:18s} 成功")
            return resp, used, log
        except Exception as e:
            last_err = e
            log.append(f"  ❌  {p['name']:18s} 失败: {type(e).__name__}: {str(e)[:80]}")
    raise RuntimeError(f"所有 provider 均失败。最后错误: {last_err}\n日志:\n" + "\n".join(log))


# ============================================================
# Agent 循环（核心）
# 导航：阅读导航_week1_week2.md → Week1 Day2 → ReAct 循环原理
# 知识：Agent 闭环 = 发消息 → 模型决定调工具还是回答 → 执行工具 → 回传结果 → 再问模型
# 原理：OpenAI Function Calling + Anthropic Tool Use 对比
#       → 阅读导航 "Anthropic Tool Use 对比" → 协议不同但语义等价
# ============================================================

def run_agent(system_prompt: str, user_query: str, max_turns: int = 5, verbose: bool = True):
    """
    [AI:Claude] Agent 闭环：
    1. 发送 system + user + tools → LLM
    2. 如果 LLM 返回 tool_calls → 执行工具 → 将结果追加到 messages → 回到步骤 1
    3. 如果 LLM 返回纯文本 → Agent 完成，返回最终回答
    4. 超过 max_turns 轮 → 强制终止

    【原子操作】Agent 循环的三段式：
    ① 调 LLM（带 tools 定义）→ ② 判断返回类型（tool_calls / text）→ ③ 执行工具并回传
    这个三段式是所有 Agent 框架（LangChain/LangGraph/MCP）的底层原语。
    详见：阅读导航 → Week1 Day2 → "ReAct 循环原理（Agent 闭环）"
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query},
    ]

    for turn in range(1, max_turns + 1):
        if verbose:
            print(f"\n── 第 {turn} 轮 ──")

        # 【原子操作①】调 LLM，带上 tools 参数
        resp, used, fallback_log = call_with_fallback(messages, tools=TOOLS)
        if verbose:
            for line in fallback_log:
                print(line)
            print(f"  → provider: {used['name']}")

        msg = resp.choices[0].message

        # 【原子操作②】判断返回类型：tool_calls = 模型要查数据，纯文本 = 模型认为可以回答
        if msg.tool_calls:
            if verbose:
                print(f"  → 模型决定调用 {len(msg.tool_calls)} 个工具")

            # 把 assistant 的 tool_calls 消息加入历史
            # 注意：tool_calls 结构必须完整保留 id/type/function，缺一不可
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })

            # 【原子操作③】执行每个工具，结果按 tool_call_id 回传
            # tool_call_id 是关键：模型用它把 tool 结果和 assistant 的 tool_calls 对应起来
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                tool_args = json.loads(tc.function.arguments)
                if verbose:
                    print(f"  🔧 {tool_name}({json.dumps(tool_args, ensure_ascii=False)})")

                result = execute_tool(tool_name, tool_args)
                if verbose:
                    total = result.get("total", "?")
                    print(f"  📊 返回 {total} 条结果")

                # role="tool" + tool_call_id 是 OpenAI 协议的规定格式
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            # 继续循环，让模型基于工具结果生成回答
            continue

        # 情况 2：模型直接返回文本（Agent 完成）
        if verbose:
            print(f"  💬 模型直接回答（第 {turn} 轮完成）")
        return msg.content, messages, turn

    return "⚠️ 达到最大轮次限制，Agent 未能在规定轮次内完成。", messages, max_turns


# ============================================================
# 演示
# ============================================================

SYSTEM_PROMPT = """你是一个 3D 打印/CNC 加工的生产调度助手。

你的能力：
- 使用 query_orders 工具查询订单信息（客户、产品、交期、环节、状态）
- 根据查询结果，用简洁专业的语言回答用户问题

规则：
- 必须用 query_orders 查询数据后再回答，不要凭空编造
- 回答时列出关键信息：订单号、客户、产品、交期、当前状态
- 如果用户问"快超期"或"紧急"，重点关注交期距今 ≤ 2 天的订单
- 用中文回答，简洁专业"""


def demo():
    queries = [
        "帮我看看有哪些快超期的订单，按交期排个序",
        "深圳精密五金有哪些订单？按数量从多到少排",
        "7月5号之前要交付的有哪些？只查在生产中的",
    ]

    for i, q in enumerate(queries, 1):
        print(f"\n{'=' * 60}")
        print(f"演示 {i}：{q}")
        print(f"{'=' * 60}")

        answer, _, turns = run_agent(SYSTEM_PROMPT, q)
        print(f"\n📋 最终回答（共 {turns} 轮）：")
        print(answer)

    print(f"\n{'=' * 60}")
    print("✅ Day 2 完成！")
    print("   Agent 闭环跑通：提问 → 调工具 → 返回数据 → LLM 格式化回答")
    print("   下一步 → Day 3：System Prompt 工程化（三层 Prompt + JSON Schema 约束）")


if __name__ == "__main__":
    print("🚀 第一周 Day 2：Function Calling / Tool Use 实战\n")

    available = [p for p in PROVIDERS if p.get("enabled") and _is_real_key(p["api_key"])]
    if not available:
        print("❌ 没有可用的 provider！请检查 .env 配置")
        sys.exit(1)

    print(f"可用 provider: {', '.join(p['name'] for p in available)}")
    print(f"已注册工具: query_orders（订单查询）\n")

    try:
        demo()
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
