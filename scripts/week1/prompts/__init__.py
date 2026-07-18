"""
prompts 包：集中管理 week1 Day3 的 Prompt 模板。

[AI:Claude] 改造：硬编码 Prompt → Jinja2 模板 + 版本常量 + render 入口

导航：阅读导航_week1_week2.md → Week1 Day3 → "Jinja2 模板 + PromptOps"
知识点：
- 系统级 Prompt：system.jinja（模型身份+能力边界+日期+安全规则）
- 场景级 Prompt：scenario_v1.jinja / scenario_v2_cot.jinja（订单规则+Few-shot/CoT）
- A/B 分流：基于 user_id 的 MD5 hash 分桶，v2_cot 占 20%，桶不漂移
"""

import hashlib
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

PROMPT_VERSION = "v1.0"

# 场景级 Prompt 版本注册表
PROMPT_VERSIONS = {
    "v1": "scenario_v1.jinja",
    "v2_cot": "scenario_v2_cot.jinja",
}

# v2_cot 流量占比（0-100），按 user_id 稳定 hash 分流
AB_V2_RATIO = 20

PROMPT_DIR = Path(__file__).parent

_jinja_env = Environment(
    loader=FileSystemLoader(PROMPT_DIR),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_template(name: str, **kwargs) -> str:
    """渲染指定 Jinja2 模板。"""
    return _jinja_env.get_template(name).render(**kwargs)


def _stable_bucket(user_id: str) -> int:
    """
    基于 MD5 的稳定分桶（0-99），避免 Python hash 随机化导致桶漂移。

    【原子操作】稳定的 A/B 分桶：
    MD5(user_id) → 取 hexdigest → 转 int → mod 100 → 0-99 的固定桶号
    同一 user_id 永远进同一桶，不会因为重启或 Python 版本变化而漂移
    """
    return int(hashlib.md5(user_id.encode("utf-8")).hexdigest(), 16) % 100


def _choose_version(user_id: str | None) -> str:
    """
    根据 user_id 决定使用哪个场景模板版本；无 user_id 时回退 v1。

    【原子操作】A/B 分流决策：
    hash(user_id) → 桶号 → 桶号 < AB_V2_RATIO(20) → v2_cot(20%)
                          → 桶号 >= 20 → v1(80%)
    """
    if user_id is None:
        return "v1"
    return "v2_cot" if _stable_bucket(user_id) < AB_V2_RATIO else "v1"


def get_user_version(user_id: str | None) -> str:
    """返回指定用户被分配到的场景模板版本（调试用）。"""
    return _choose_version(user_id)


def get_system_prompt(today: str) -> str:
    """渲染系统级 Prompt。"""
    return render_template("system.jinja", today=today)


def get_scenario_prompt(user_id: str | None = None, today: str | None = None) -> str:
    """
    渲染场景级 Prompt。
    根据 user_id 做 A/B 分流：AB_V2_RATIO 比例进入 v2_cot，其余走 v1。
    """
    version = _choose_version(user_id)
    return render_template(PROMPT_VERSIONS[version], today=today or "")
