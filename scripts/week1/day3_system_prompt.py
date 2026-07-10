"""
第一周 · Day 3 — System Prompt 工程化
==================================================
目标：把 Day 2 的单一 SYSTEM_PROMPT 升级为三层架构（系统级/场景级/用户级），
      让模型行为可预测、输出可解析，并修复 Day 2 演示 3 的年份 bug。

核心认知：Prompt 是工程化产物——角色设定 + 能力边界 + 输出约束 + 安全规则 + 上下文注入。
        不是"随便写句话"，而是有结构、有版本、可维护的代码资产。

三层 Prompt 架构（本日核心）：
  系统级（固定不变）：模型身份 + 能力边界 + 当前日期 + 安全规则
  场景级（可配置）  ：订单查询场景规则 + 输出格式 + Few-shot 示例
  用户级（动态注入）：用户输入，用 XML 标签隔离防 Prompt Injection

修复的 bug：Day 2 演示 3 模型把"7月5号"填成 2025-07-05 → 系统级注入当前日期解决。

[AI:Claude] 架构设计：三层 Prompt + 日期上下文注入 + XML 标签隔离
[AI:Claude] 改造：硬编码 Prompt → Jinja2 模板（scripts/week1/prompts/）
"""

import json
import sys
from datetime import date

# 沿用 Day 2 的主备架构 + 工具 + Agent 调用能力（在同目录）
from day2_function_calling import (
    PROVIDERS,
    TOOLS,
    _is_real_key,
    call_with_fallback,
    execute_tool,
    query_orders,
)
from prompts import get_scenario_prompt, get_system_prompt, get_user_version


# ============================================================
# 第一部分：三层 Prompt 架构（本日核心）
# ============================================================

def build_user_message(user_query: str) -> str:
    """
    用户级 Prompt：用 XML 标签包裹用户输入，与系统指令隔离。
    防止 Prompt Injection——即使用户输入"忽略以上规则"，模型也能识别这是 user_input 内的数据而非真实指令。
    """
    return f"<user_input>{user_query}</user_input>"


def build_system_prompt(today: str | None = None, user_id: str | None = None) -> str:
    """
    组装三层 Prompt：系统级 + 场景级（用户级在 run_agent 里注入）。
    场景级根据 user_id 做 A/B 分流。
    """
    if today is None:
        today = date.today().isoformat()
    return get_system_prompt(today) + "\n" + get_scenario_prompt(user_id=user_id, today=today)


# ============================================================
# 第二部分：Agent 循环（Day 2 升级——用三层 Prompt）
# ============================================================

def run_agent(system_prompt: str, user_query: str, max_turns: int = 5, verbose: bool = True):
    """
    [AI:Claude] Agent 闭环（Day 3 升级版）：
    与 Day 2 的差异只在 messages 初始化——
    system 用三层架构构建，user 用 XML 标签隔离。
    循环体（tool_calls 处理）完全沿用 Day 2。
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": build_user_message(user_query)},
    ]

    for turn in range(1, max_turns + 1):
        if verbose:
            print(f"\n── 第 {turn} 轮 ──")

        resp, used, fallback_log = call_with_fallback(messages, tools=TOOLS)
        if verbose:
            for line in fallback_log:
                print(line)
            print(f"  → provider: {used['name']}")

        msg = resp.choices[0].message

        # 情况 1：模型要调工具
        if msg.tool_calls:
            if verbose:
                print(f"  → 模型决定调用 {len(msg.tool_calls)} 个工具")

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

            for tc in msg.tool_calls:
                tool_name = tc.function.name
                tool_args = json.loads(tc.function.arguments)
                if verbose:
                    print(f"  🔧 {tool_name}({json.dumps(tool_args, ensure_ascii=False)})")

                result = execute_tool(tool_name, tool_args)
                if verbose:
                    total = result.get("total", "?")
                    print(f"  📊 返回 {total} 条结果")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            continue

        # 情况 2：模型直接返回文本（Agent 完成）
        if verbose:
            print(f"  💬 模型直接回答（第 {turn} 轮完成）")
        return msg.content, messages, turn

    return "⚠️ 达到最大轮次限制，Agent 未能在规定轮次内完成。", messages, max_turns


# ============================================================
# 第三部分：JSON Schema 输出约束（Prompt 级）
# ============================================================

STRUCTURED_SYSTEM = """你是生产调度助手。把给定的订单数据严格按以下 JSON schema 输出：

{
  "summary": "一句话总结查询结论",
  "count": 订单数量(整数),
  "orders": [
    {
      "id": "订单号",
      "客户": "客户名",
      "产品": "产品名",
      "数量": 数量(整数),
      "交期": "YYYY-MM-DD",
      "环节": "当前环节",
      "状态": "订单状态"
    }
  ],
  "suggestion": "调度建议"
}

要求：
- 只输出 JSON，不要 Markdown 代码块、不要解释文字
- 所有字段必填，数量为整数
"""


def demo_structured_output():
    """
    演示 JSON Schema 输出约束（Prompt 级）。
    先用代码查出真实数据，再让模型按 schema 格式化为 JSON——
    生产环境可改用 response_format={type:"json_object"} 或 strict mode 强约束。
    """
    print("\n" + "=" * 60)
    print("JSON Schema 输出约束演示（Prompt 级）")
    print("=" * 60)

    data = query_orders(status="即将超期", sort_by="交期")
    print(f"原始数据（{data['total']} 条）：已查出")

    messages = [
        {"role": "system", "content": STRUCTURED_SYSTEM},
        {"role": "user", "content": f"订单数据：\n{json.dumps(data, ensure_ascii=False, indent=2)}"},
    ]
    resp, used, _ = call_with_fallback(messages)
    raw = resp.choices[0].message.content

    print(f"\n模型输出（按 schema）：")
    print(raw)

    try:
        parsed = json.loads(raw)
        print(f"\n✅ JSON 解析成功：summary={parsed.get('summary')}，count={parsed.get('count')}")
    except json.JSONDecodeError as e:
        print(f"\n⚠️ JSON 解析失败：{e}（Prompt 级约束非 100% 可靠，生产用 strict mode）")


# ============================================================
# 演示
# ============================================================

def demo():
    """四个演示场景：前三个验证年份 bug / A/B 分流，第四个演示多约束 CoT"""
    queries = [
        ("bob", "帮我看看有哪些快超期的订单，按交期排个序"),
        ("carol", "深圳精密五金有哪些订单？按数量从多到少排"),
        ("dave", "7月5号之前要交付的有哪些？只查在生产中的"),  # Day 2 的 bug 场景
        ("alice", "优先处理快超期且数量大于300的订单，按交期排序并给出处理建议"),  # CoT 多约束场景
    ]

    for user_id, q in queries:
        version = get_user_version(user_id)
        print(f"\n{'=' * 60}")
        print(f"用户 {user_id} → 场景模板版本: {version}")
        print(f"演示：{q}")
        print(f"{'=' * 60}")

        system_prompt = build_system_prompt(user_id=user_id)
        answer, _, turns = run_agent(system_prompt, q)
        print(f"\n📋 最终回答（共 {turns} 轮）：")
        print(answer)

    print(f"\n{'=' * 60}")
    print("✅ Day 3 完成！")
    print("   三层 Prompt 架构落地：系统级（含日期）+ 场景级（含 Few-shot/CoT）+ 用户级（XML 隔离）")
    print("   Prompt 版本 + A/B 分流已启用（v2_cot 含 <thinking> 引导）")
    print("   下一步 → Day 4：原理速览 + 本周消化（Token/Context/Temperature）")


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    print("🚀 第一周 Day 3：System Prompt 工程化\n")

    available = [p for p in PROVIDERS if p.get("enabled") and _is_real_key(p["api_key"])]
    if not available:
        print("❌ 没有可用的 provider！请检查 .env 配置")
        sys.exit(1)

    print(f"可用 provider: {', '.join(p['name'] for p in available)}")
    print(f"当前日期注入: {date.today().isoformat()}")
    print()

    try:
        demo()
        demo_structured_output()
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
