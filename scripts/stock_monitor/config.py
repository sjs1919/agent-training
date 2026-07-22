"""
配置加载模块：读取 sock.yml 和 .env，产出类型安全的 AppConfig。
包含 LLM provider 列表（从 .env 读取，与 day1_api_basics.py 保持一致）。
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import yaml
from dotenv import load_dotenv


@dataclass
class ProviderConfig:
    """单个 LLM provider 配置（OpenAI 兼容协议）"""
    name: str
    enabled: bool
    api_key: str
    base_url: str
    model: str
    note: str = ""


@dataclass
class EmailConfig:
    enabled: bool = True
    subject_prefix: str = "[股票监控]"
    to_emails: List[str] = field(default_factory=list)
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    from_name: str = "Stock-Monitor"


@dataclass
class MonitorConfig:
    check_interval_seconds: int = 600  # 10分钟扫一次
    trading_start: str = "09:00"
    trading_end: str = "15:30"


@dataclass
class AppConfig:
    stocks: List[str] = field(default_factory=list)
    moving_averages: List[int] = field(default_factory=lambda: [5, 10, 20])
    monitor: MonitorConfig = field(default_factory=MonitorConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    providers: List[ProviderConfig] = field(default_factory=list)


def _is_real_key(key: str) -> bool:
    """判断 key 是否为真实配置（非空、非占位符）"""
    if not key:
        return False
    return "your-" not in key.lower()


def _build_providers() -> List[ProviderConfig]:
    """从 .env 构建 LLM provider 列表（与 day1_api_basics.py 保持一致）。"""
    return [
        ProviderConfig(
            name="火山豆包(coding)",
            enabled=True,
            api_key=os.getenv("VOLC_API_KEY", ""),
            base_url=os.getenv("VOLC_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding/v3"),
            model=os.getenv("VOLC_MODEL", "ark-code-latest"),
            note="主用 · 字节编程套餐",
        ),
        ProviderConfig(
            name="DeepSeek",
            enabled=True,
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            note="备用1 · ¥1/百万Token",
        ),
        ProviderConfig(
            name="Kimi(coding)",
            enabled=os.getenv("KIMI_ENABLED", "false").lower() == "true",
            api_key=os.getenv("KIMI_API_KEY", ""),
            base_url=os.getenv("KIMI_BASE_URL", "https://api.kimi.com/coding/v1"),
            model=os.getenv("KIMI_MODEL", "kimi-for-coding"),
            note="备用2 · 会员过期暂禁用",
        ),
    ]


def load_config(sock_yml_path: str = None, env_path: str = None) -> AppConfig:
    """加载 sock.yml 和 .env，返回 AppConfig 实例。"""
    project_root = Path(__file__).resolve().parent.parent.parent

    # 加载 .env
    env_file = Path(env_path) if env_path else project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    # 加载 sock.yml
    yml_file = Path(sock_yml_path) if sock_yml_path else project_root / "sock.yml"
    yml_config: dict = {}
    if yml_file.exists():
        with open(yml_file, "r", encoding="utf-8") as f:
            yml_config = yaml.safe_load(f) or {}

    # EmailConfig
    email_cfg = EmailConfig()
    e = yml_config.get("email", {})
    email_cfg.enabled = e.get("enabled", True)
    email_cfg.subject_prefix = e.get("subject_prefix", "[股票监控]")
    email_cfg.to_emails = e.get("to_emails", [])
    email_cfg.smtp_host = os.getenv("SMTP_HOST", "smtp.qq.com")
    email_cfg.smtp_port = int(os.getenv("SMTP_PORT", "587"))
    email_cfg.username = os.getenv("SMTP_USERNAME", "")
    email_cfg.password = os.getenv("SMTP_PASSWORD", "")
    email_cfg.from_name = os.getenv("SMTP_FROM_NAME", "Stock-Monitor")

    # MonitorConfig
    monitor_cfg = MonitorConfig()
    m = yml_config.get("monitor", {})
    monitor_cfg.check_interval_seconds = m.get("check_interval_seconds", 600)
    monitor_cfg.trading_start = m.get("trading_start", "09:00")
    monitor_cfg.trading_end = m.get("trading_end", "15:30")

    return AppConfig(
        stocks=yml_config.get("stocks", []),
        moving_averages=yml_config.get("moving_averages", [5, 10, 20]),
        monitor=monitor_cfg,
        email=email_cfg,
        providers=_build_providers(),
    )


def get_enabled_providers(config: AppConfig) -> List[ProviderConfig]:
    """返回所有已启用且 key 有效的 provider。"""
    return [p for p in config.providers if p.enabled and _is_real_key(p.api_key)]
