"""
AI 摘要模块：收盘后使用 LLM 生成市场整体摘要 + 个股走势摘要。
两份数据输入 LLM：
  1. akshare 原始指标（价格/涨跌幅/均线/成交量/振幅）
  2. 最近5日走势轨迹（日期+收盘价+涨跌幅）
LLM 基于真实数据生成自然语言总结，而非模板拼接。
"""
import json
from datetime import datetime
from typing import Dict

from scripts.stock_monitor.config import AppConfig
from scripts.stock_monitor.data_fetcher import (
    get_code_name_map,
    build_stock_snapshot,
    build_market_snapshot,
)
from scripts.stock_monitor.llm_client import call_with_fallback


MARKET_SYSTEM_PROMPT = """你是一位资深的A股市场分析师。请根据提供的市场数据，用4-6句话总结当日市场整体走势。

要求：
1. 先说三大指数（上证、创业板、科创50）各自涨跌和成交额，对比前日变化（量能环比）
2. 再点评全市场情绪：涨跌比、中位数收益、总成交额及环比
3. 分析板块风格（权重/小盘、成长/价值谁强谁弱）
4. 如有明显异常（放量/缩量、恐慌/亢奋、极端中位数），简要提及
5. 纯文本输出，不要用markdown格式，数据点到为止不堆砌
"""

STOCK_SYSTEM_PROMPT = """你是一位专业的A股个股分析师。请根据提供的股票数据（指标 + 近5日走势轨迹），用2-3句话分析该股当日表现。

要求：
1. 描述当天走势特征（高开低走/低开高走/震荡/单边等）
2. 指出与关键均线（MA5/MA10/MA20）的位置关系
3. 点评量价配合情况（放量上涨/缩量下跌等）
4. 纯文本输出，不要用markdown格式，不堆砌数字
"""


def _build_market_prompt(snapshot: dict) -> str:
    """构建市场摘要的 LLM prompt，包含三大指数+全市场统计。"""
    parts = ["以下是今日A股市场数据：", ""]

    # --- 三大指数 + 中证全指 ---
    indices = snapshot.get("indices", {})
    index_order = [
        ("sh000001", "上证指数"),
        ("sz399006", "创业板指"),
        ("sh000688", "科创50"),
        ("sh000985", "中证全指"),
    ]
    for key, label in index_order:
        idx = indices.get(key, {})
        if idx:
            parts.append(f"【{label}】")
            parts.append(json.dumps(idx, ensure_ascii=False, default=str))

    # --- 全市场统计 ---
    breadth = snapshot.get("breadth", {})
    if breadth:
        parts.append("")
        parts.append("【全市场统计】")
        parts.append(json.dumps(breadth, ensure_ascii=False, default=str))

    parts.append(f"\n日期：{datetime.now().strftime('%Y-%m-%d')}")
    parts.append("\n请基于以上数据，用4-6句话总结今日A股市场整体走势。")
    return "\n".join(parts)


def _build_stock_prompt(snapshot: dict) -> str:
    """构建个股摘要的 LLM prompt。（两份数据合一）"""
    parts = [
        f"以下是 {snapshot.get('name', '')}({snapshot.get('code', '')}) 今日数据：",
        "",
        "【akshare原始指标】",
        json.dumps({
            "price": snapshot.get("price"),
            "change": snapshot.get("change"),
            "volume": snapshot.get("volume"),
            "ma": snapshot.get("ma"),
        }, ensure_ascii=False, default=str),
        "",
        "【近5日走势轨迹】",
    ]
    for t in snapshot.get("trajectory", []):
        pct = t.get('change_pct', 0)
        if isinstance(pct, (int, float)):
            parts.append(f"  {t['date']} 收盘{t['close']} 涨跌{pct:.2f}%")
        else:
            parts.append(f"  {t['date']} 收盘{t['close']}")

    parts.append(f"\n日期：{datetime.now().strftime('%Y-%m-%d')}")
    parts.append("\n请基于以上数据，用2-3句话分析该股当日表现。")
    return "\n".join(parts)


def generate_market_summary(config: AppConfig) -> str:
    """使用 LLM 生成当天市场整体走势摘要。"""
    snapshot = build_market_snapshot()
    if not snapshot.get("indices") and not snapshot.get("breadth"):
        return "无法获取市场数据"

    user_prompt = _build_market_prompt(snapshot)
    try:
        content, provider, log = call_with_fallback(
            config, MARKET_SYSTEM_PROMPT, user_prompt, max_tokens=600, temperature=0.3,
        )
        print(f"[摘要] 市场摘要 → {provider.name}")
        for line in log:
            print(line)
        return content.strip()
    except Exception as e:
        print(f"[摘要] LLM调用失败: {e}")
        breadth = snapshot.get("breadth", {})
        return (
            f"今日市场：上涨{breadth.get('up', '?')}家，"
            f"下跌{breadth.get('down', '?')}家，平盘{breadth.get('flat', '?')}家"
        )


def generate_stock_summary(config: AppConfig, code: str, name: str) -> str:
    """使用 LLM 生成单只股票当日走势摘要。"""
    snapshot = build_stock_snapshot(code, name)
    if "error" in snapshot:
        return f"{name}({code})：{snapshot['error']}"

    user_prompt = _build_stock_prompt(snapshot)
    try:
        content, provider, log = call_with_fallback(
            config, STOCK_SYSTEM_PROMPT, user_prompt, max_tokens=500, temperature=0.3,
        )
        for line in log:
            print(line)
        return content.strip()
    except Exception as e:
        print(f"[摘要] {code} LLM调用失败: {e}")
        price = snapshot.get("price", {})
        change = snapshot.get("change", {})
        return (
            f"{name}({code})：收盘{price.get('close', '?')}，"
            f"涨跌{change.get('pct', 0):.2f}%"
        )


def generate_all_summaries(config: AppConfig) -> Dict[str, str]:
    """为所有自选股生成AI摘要。返回 {code: summary_str}。"""
    name_map = get_code_name_map()
    summaries: Dict[str, str] = {}
    for code in config.stocks:
        name = name_map.get(code, code)
        print(f"[摘要] 正在为 {name}({code}) 生成AI摘要...")
        summaries[code] = generate_stock_summary(config, code, name)
    return summaries
