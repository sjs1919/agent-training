"""
第一周 · Day 1 — 大模型 API 入门（主备多 Provider 架构）
=========================================================
目标：跑通 API 调用，理解 OpenAI 兼容协议的全链路；
      并建立"主备 fallback"能力 —— 主调失败自动切备用 provider。

核心认知：所有 OpenAI 兼容 provider，底层模式一致 ——
        model → messages → 推理 → 返回。
        学会一套协议 = 掌握 DeepSeek、Kimi、豆包、Qwen 等国产模型。

主备架构（企业级 Agent 必备）：
  主  火山豆包 coding  字节编程套餐，响应快（已升级）
  备  DeepSeek        ¥1/百万Token，性价比高
  备  Kimi coding      会员过期暂禁用（KIMI_ENABLED=false）

[AI:Claude] 架构设计：统一 call_llm() + 链式 fallback
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import httpx

# Windows 默认 stdout 走 GBK，编码不了 emoji/部分中文 -> 切 UTF-8（开箱即跑）
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent.parent / ".env")

# ============================================================
# Provider 注册表：每个 provider 一份配置
# 新增 provider 只需在此追加一项，call_llm 自动支持
# ============================================================

PROVIDERS = [
    {
        "name": "火山豆包(coding)",
        "enabled": True,
        "api_key": os.getenv("VOLC_API_KEY", ""),
        "base_url": os.getenv("VOLC_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding/v3"),
        "model": os.getenv("VOLC_MODEL", "ark-code-latest"),
        "note": "主用 · 字节编程套餐 · 端点 /api/coding/v3",
    },
    {
        "name": "DeepSeek",
        "enabled": True,
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "note": "备用1 · ¥1/百万Token · OpenAI 兼容",
    },
    {
        "name": "Kimi(coding)",
        "enabled": os.getenv("KIMI_ENABLED", "false").lower() == "true",
        "api_key": os.getenv("KIMI_API_KEY", ""),
        "base_url": os.getenv("KIMI_BASE_URL", "https://api.kimi.com/coding/v1"),
        "model": os.getenv("KIMI_MODEL", "kimi-for-coding"),
        "note": "备用2 · 会员过期暂禁用 · 续费后改 KIMI_ENABLED=true",
    },
]


def _is_real_key(key: str) -> bool:
    """判断 key 是否为真实配置（非空、非占位符）"""
    if not key:
        return False
    return "your-" not in key.lower()


# ============================================================
# 第一部分：统一调用函数（核心）
# 导航：阅读导航_week1_week2.md → Week1 Day1 → "读完对照" call_llm()
# 知识：OpenAI Chat Completions API → messages(role/content) → model → response
# ============================================================

def call_llm(provider, system_prompt, user_prompt, max_tokens=200, temperature=0.3):
    """
    用指定 provider 调用一次 LLM。
    所有 OpenAI 兼容 provider 走同一段代码，只差 client 配置。
    返回 (response, provider) 或抛出异常。

    【原子操作】OpenAI 兼容协议的核心调用模式：
    client = OpenAI(api_key, base_url) → client.chat.completions.create(model, messages, ...)
    豆包/DeepSeek/Kimi 三家 base_url 不同，但这一行代码完全相同。
    """
    if not provider.get("enabled"):
        raise RuntimeError(f"provider {provider['name']} 已禁用")
    if not _is_real_key(provider["api_key"]):
        raise RuntimeError(f"provider {provider['name']} key 未配置")

    # 【原子操作】创建 OpenAI 兼容客户端
    # trust_env=False 是关键：绕过 Windows 系统代理设置，避免死代理导致 SSL EOF
    # 详见：阅读导航 → Week1 Day1 → httpx trust_env 与系统代理（踩坑复盘）
    client = OpenAI(
        api_key=provider["api_key"],
        base_url=provider["base_url"],
        http_client=httpx.Client(trust_env=False),
    )
    # 【原子操作】chat.completions.create — 所有 OpenAI 兼容 API 的统一入口
    # messages 结构：system(角色设定) + user(用户问题)，后续 Day2/3 会扩展 tool_calls
    response = client.chat.completions.create(
        model=provider["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response, provider


def call_with_fallback(system_prompt, user_prompt, max_tokens=200, temperature=0.3):
    """
    [AI:Claude] 主备 fallback：按 PROVIDERS 顺序逐个尝试，第一个成功即返回。
    主调失败（网络/限流/鉴权）自动切下一个备用 provider。
    返回 (response, provider, fallback_log)

    【原子操作】企业级 Agent 的主备切换模式：
    for provider in PROVIDERS:
        try: call_llm(provider) → 成功即返回
        except: 记录日志 → 继续下一个
    核心价值：主调限流/故障时业务不中断，切换成本几乎为零（同协议）
    详见：阅读导航 → Week1 Day1 → "读完对照" call_with_fallback 的 try/except 链路
    """
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
            resp, used = call_llm(p, system_prompt, user_prompt, max_tokens, temperature)
            log.append(f"  ✅  {p['name']:18s} 成功")
            return resp, used, log
        except Exception as e:
            last_err = e
            log.append(f"  ❌  {p['name']:18s} 失败: {type(e).__name__}: {str(e)[:80]}")
    raise RuntimeError(f"所有 provider 均失败。最后错误: {last_err}\n日志:\n" + "\n".join(log))


# ============================================================
# 第二部分：单 provider 调用演示（理解协议）
# ============================================================

def demo_single_provider():
    """用主 provider 跑一次，展示 OpenAI 兼容协议的完整响应结构"""
    print("=" * 60)
    print("单 Provider 调用演示（火山豆包 主用）")
    print("=" * 60)

    p = PROVIDERS[0]
    print(f"provider : {p['name']}")
    print(f"base_url : {p['base_url']}")
    print(f"model    : {p['model']}")
    print("-" * 60)

    resp, used = call_llm(
        p,
        system_prompt="你是一个 3D 打印生产调度助手，回答简洁专业。",
        user_prompt="简述 3D 打印 CNC 加工后处理的主要步骤，50字以内。",
    )

    print(f"模型     : {resp.model}")
    print(f"输入Token: {resp.usage.prompt_tokens}")
    print(f"输出Token: {resp.usage.completion_tokens}")
    print(f"总Token  : {resp.usage.total_tokens}")
    print(f"停因     : {resp.choices[0].finish_reason}")
    print("-" * 60)
    print(resp.choices[0].message.content)
    print("-" * 60)


# ============================================================
# 第三部分：主备 fallback 演示
# ============================================================

def demo_fallback():
    """
    [AI:Claude] 演示主备自动切换。
    先正常调（主 火山豆包 成功）；
    再故意把主 provider key 改坏，模拟主调失败 → 自动切 DeepSeek 备用。
    """
    print("\n" + "=" * 60)
    print("主备 fallback 演示")
    print("=" * 60)

    SYS = "你是一个 3D 打印生产调度助手，回答简洁专业。"
    USER = "用 15 字以内说明 3D 打印后处理的关键步骤。"

    # 1) 正常路径：主 火山豆包 应直接成功
    print("\n场景 1：主 provider 正常 → 主调成功")
    resp, used, log = call_with_fallback(SYS, USER, max_tokens=150)
    for line in log:
        print(line)
    print(f"  → 实际使用: {used['name']}")
    print(f"  → 内容: {resp.choices[0].message.content}")

    # 2) 故意制造主调失败：把主 provider 的 key 改坏
    print("\n场景 2：主 provider key 失效 → 自动切备用")
    broken = dict(PROVIDERS[0])
    broken["api_key"] = "sk-invalid-key-for-fallback-demo"
    saved = PROVIDERS[0]
    PROVIDERS[0] = broken
    try:
        resp, used, log = call_with_fallback(SYS, USER, max_tokens=150)
        for line in log:
            print(line)
        print(f"  → 实际使用: {used['name']}")
        print(f"  → 内容: {resp.choices[0].message.content}")
    finally:
        PROVIDERS[0] = saved  # 恢复真实配置


# ============================================================
# 第四部分：协议对比（认知总结）
# ============================================================

def show_protocol_summary():
    """打印 OpenAI 兼容协议核心字段 + 多 provider 切换认知"""
    print("\n" + "=" * 60)
    print("协议认知总结")
    print("=" * 60)
    print("""
┌──────────────────┬─────────────────────────────────────────┐
│ 维度             │ OpenAI 兼容协议（本训练主轴）           │
├──────────────────┼─────────────────────────────────────────┤
│ 端点             │ {base_url}/chat/completions              │
│ system prompt    │ messages 中的 role=system               │
│ 停因字段         │ finish_reason                           │
│ Token 统计       │ prompt_tokens / completion_tokens       │
│ Tool Use         │ tools 数组                              │
└──────────────────┴─────────────────────────────────────────┘

🎯 关键认知：
   所有 OpenAI 兼容 provider，代码层只差 base_url + api_key + model。
   学会一套协议 = 掌握 DeepSeek / Kimi / 豆包 / Qwen / GLM 等国产模型。

📌 主备架构价值：
   - 主调限流/故障时业务不中断
   - 不同模型能力互补（DeepSeek 性价比，豆包响应快）
   - 切换成本几乎为零（同协议）
""")
    print("当前 provider 状态：")
    for p in PROVIDERS:
        flag = "✅" if (p.get("enabled") and _is_real_key(p["api_key"])) else "⏸️"
        print(f"  {flag} {p['name']:18s} {p['note']}")


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    print("🚀 第一周 Day 1：大模型 API 入门（主备多 Provider）\n")

    # 至少要有一个可用 provider
    available = [p for p in PROVIDERS if p.get("enabled") and _is_real_key(p["api_key"])]
    if not available:
        print("❌ 没有可用的 provider！请检查 .env 配置")
        sys.exit(1)

    try:
        demo_single_provider()
        demo_fallback()
        show_protocol_summary()

        print("\n✅ Day 1 完成！")
        print("   下一步 → Day 2：Function Calling / Tool Use 实战")
        print("   主备 fallback 已就绪，后续 Day 在同一架构上叠加能力")

    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        sys.exit(1)
