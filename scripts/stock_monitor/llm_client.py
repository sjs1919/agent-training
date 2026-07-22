"""
LLM 调用基础组件 + 连接池。
每个 enabled provider 预创建一个 OpenAI client（含 httpx 连接池），
避免每次调用重新建立 TCP 连接。

[AI:Claude] 架构设计：复用 day1_api_basics.py 的主备 fallback 模式，
抽取为独立模块供 summarizer.py 等模块导入。
"""
from typing import List, Tuple

import httpx
from openai import OpenAI

from scripts.stock_monitor.config import ProviderConfig, AppConfig

# 全局客户端缓存：{provider_name: OpenAI}
_client_pool: dict = {}


def init_clients(config: AppConfig):
    """
    初始化 LLM 客户端连接池。
    为每个已启用的 provider 预创建一个 OpenAI client 实例。
    应在程序启动时调用一次。
    """
    global _client_pool
    _client_pool.clear()

    for p in config.providers:
        if not p.enabled or "your-" in p.api_key.lower():
            continue
        # [AI:Claude] trust_env=False 是关键：绕过 Windows 系统代理，避免死代理导致 SSL EOF
        http_client = httpx.Client(
            trust_env=False,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            timeout=httpx.Timeout(120.0),
        )
        _client_pool[p.name] = OpenAI(
            api_key=p.api_key,
            base_url=p.base_url,
            http_client=http_client,
        )
        print(f"[LLM] 客户端就绪: {p.name} ({p.model})")

    if not _client_pool:
        print("[LLM] 警告：没有可用的 LLM provider！")


def call_llm(
    provider: ProviderConfig,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> Tuple[str, ProviderConfig]:
    """
    用指定 provider 调用一次 LLM，返回 (响应文本, provider)。
    从连接池复用 OpenAI client，不每次新建。
    """
    client = _client_pool.get(provider.name)
    if client is None:
        raise RuntimeError(f"provider {provider.name} 客户端未初始化，请先调用 init_clients()")

    response = client.chat.completions.create(
        model=provider.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    choice = response.choices[0]
    content = choice.message.content or ""

    # 诊断：检测截断和空返回
    if choice.finish_reason == "length":
        print(f"  ⚠️  {provider.name} 输出被截断 (finish_reason=length, max_tokens={max_tokens})")
    if not content:
        print(f"  ⚠️  {provider.name} 返回空内容 (finish_reason={choice.finish_reason})")

    return content, provider


def call_with_fallback(
    config: AppConfig,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> Tuple[str, ProviderConfig, List[str]]:
    """
    主备 fallback：按 providers 顺序逐个尝试，第一个成功即返回。
    返回 (响应文本, 使用的provider, fallback日志)。
    """
    log: List[str] = []
    last_err = None

    for p in config.providers:
        if not p.enabled:
            log.append(f"  ⏭️  {p.name} 跳过（已禁用）")
            continue
        if "your-" in p.api_key.lower():
            log.append(f"  ⏭️  {p.name} 跳过（key未配置）")
            continue
        try:
            content, used = call_llm(p, system_prompt, user_prompt, max_tokens, temperature)
            log.append(f"  ✅  {p.name} 成功")
            return content, used, log
        except Exception as e:
            last_err = e
            log.append(f"  ❌  {p.name} 失败: {type(e).__name__}: {str(e)[:80]}")

    raise RuntimeError(f"所有 provider 均失败。最后错误: {last_err}\n日志:\n" + "\n".join(log))


def close_clients():
    """关闭所有客户端连接池（程序退出时调用）。"""
    global _client_pool
    for name, client in _client_pool.items():
        client.close()
    _client_pool.clear()
    print("[LLM] 所有客户端已关闭")
