"""
第一周 · Day 4 — 原理速览：Token / Context Window / Temperature
==============================================================
目标：理解模型背后的三个"物理量"，为 week1 收尾和 week2 RAG 做原理铺垫。

核心认知：
  Token ≠ 字符 ≠ 单词，是模型的最小处理单元
  Context Window 不是越大越好， Attention 是 O(n²)
  Temperature 控制采样随机性，事实/代码要低，创意/发散要高

[AI:Claude] 设计：Token 计数 + Context 对比 + Temperature 实验
"""

import sys
from datetime import date

# 沿用 week1 主备调用与 Prompt 构造能力
from day2_function_calling import (
    PROVIDERS,
    SYSTEM_PROMPT as DAY2_SYSTEM_PROMPT,
    _is_real_key,
    call_with_fallback,
)
from day3_system_prompt import build_system_prompt, build_user_message

# Windows 默认 stdout 走 GBK，编码不了 emoji/部分中文 -> 切 UTF-8（开箱即跑）
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

DAY1_SYSTEM_PROMPT = "你是一个 3D 打印生产调度助手，回答简洁专业。"
DAY1_USER_PROMPT = "简述 3D 打印 CNC 加工后处理的主要步骤，50字以内。"

DAY2_USER_PROMPT = "有哪些快超期的订单？"

DAY3_USER_PROMPT = "优先处理快超期且数量大于300的订单，按交期排序并给出处理建议。"


def _get_encoder():
    """获取 tiktoken encoder；未安装时给出安装提示。"""
    try:
        import tiktoken
        return tiktoken
    except ImportError as e:
        print("❌ 缺少 tiktoken，请先安装：pip install tiktoken")
        raise e


def count_tokens(messages, model: str = "gpt-4o") -> int:
    """
    估算 messages 的 token 数。
    说明：不同 provider 使用不同 tokenizer，这里用 cl100k_base / gpt-4o 做近似估算。
    """
    tiktoken = _get_encoder()
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    total = 0
    for msg in messages:
        # 每条消息的开销：role / content 分隔等
        total += 3
        for key, value in msg.items():
            total += len(encoding.encode(str(value)))
            if key == "name":
                total -= 1
    total += 3  # 回复前缀开销
    return total


def demo_token_counting():
    """对比 Day1/2/3 三个 demo 的输入 token 消耗。"""
    print("=" * 60)
    print("Token 计数对比（输入 prompt）")
    print("=" * 60)

    cases = [
        (
            "Day 1 单 provider 调用",
            [
                {"role": "system", "content": DAY1_SYSTEM_PROMPT},
                {"role": "user", "content": DAY1_USER_PROMPT},
            ],
        ),
        (
            "Day 2 Function Calling Agent",
            [
                {"role": "system", "content": DAY2_SYSTEM_PROMPT},
                {"role": "user", "content": DAY2_USER_PROMPT},
            ],
        ),
        (
            "Day 3 三层 Prompt（v2_cot / alice）",
            [
                {"role": "system", "content": build_system_prompt(user_id="alice")},
                {"role": "user", "content": build_user_message(DAY3_USER_PROMPT)},
            ],
        ),
    ]

    for name, messages in cases:
        tokens = count_tokens(messages)
        print(f"\n{name}")
        print(f"  估算输入 token: {tokens}")
        print(f"  按豆包/DeepSeek 约 ¥1-2/百万 token，单次输入成本 ≈ {tokens * 0.000002:.6f} 元")

    # 直观感受：中文 token 密度
    sample_text = "3D打印 CNC加工"
    encoding = _get_encoder().encoding_for_model("gpt-4o")
    encoded = encoding.encode(sample_text)
    print(f"\n直观示例：\"{sample_text}\" → {len(encoded)} tokens: {encoded}")
    print("  说明：中文通常 1 汉字 ≈ 1.5-2 token，英文平均 4 字符 / token")


def demo_context_window():
    """展示常见模型的上下文窗口与长窗口成本。"""
    print("\n" + "=" * 60)
    print("Context Window 对比")
    print("=" * 60)

    models = [
        ("豆包 ark-code-latest", "128K", "OpenAI 兼容"),
        ("DeepSeek-V3 / deepseek-chat", "64K", "OpenAI 兼容"),
        ("GPT-4o", "128K", "OpenAI"),
        ("Claude 3.5 Sonnet", "200K", "Anthropic"),
        ("Kimi k1.5", "256K", "Moonshot"),
    ]

    print("\n| 模型 | 上下文窗口 | 协议 |")
    print("|---|---|---|")
    for name, window, protocol in models:
        print(f"| {name} | {window} | {protocol} |")

    print("""
关键认知：
- 窗口大小 = 输入 + 输出 token 的总上限。
- Attention 计算复杂度约 O(n²)，窗口翻倍 → 计算/延迟/成本翻约 4 倍。
- 长文本不要硬塞，优先用：摘要压缩 / 检索召回 / 结构化分段。
""")


def demo_temperature():
    """用同一条 prompt 跑不同 temperature，观察输出差异。"""
    print("\n" + "=" * 60)
    print("Temperature 对比实验")
    print("=" * 60)

    system_prompt = "你是一个 3D 打印/CNC 加工生产调度专家，回答简洁。"
    user_prompt = "用一句话说明：当订单交期和产线产能冲突时，优先保哪个？并给出理由。"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    temperatures = [0.3, 0.7, 1.0]
    for temp in temperatures:
        print(f"\n--- temperature = {temp} ---")
        resp, used, log = call_with_fallback(messages, temperature=temp, max_tokens=200)
        for line in log:
            print(line)
        print(f"  → provider: {used['name']}")
        print(f"  → 输出: {resp.choices[0].message.content.strip()}")


def main():
    print("🚀 第一周 Day 4：Token / Context Window / Temperature\n")

    available = [p for p in PROVIDERS if p.get("enabled") and _is_real_key(p["api_key"])]
    if not available:
        print("❌ 没有可用的 provider！temperature 实验将跳过，仅做 Token/Context 部分。")
        demo_token_counting()
        demo_context_window()
        return

    print(f"可用 provider: {', '.join(p['name'] for p in available)}")
    print(f"当前日期: {date.today().isoformat()}\n")

    try:
        demo_token_counting()
        demo_context_window()
        demo_temperature()

        print("\n" + "=" * 60)
        print("✅ Day 4 完成！")
        print("   理解 Token / Context / Temperature 三个物理量")
        print("   下一步 → week2：RAG + Agent 概念")

    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
