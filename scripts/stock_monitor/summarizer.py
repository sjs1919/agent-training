"""
AI 摘要模块：收盘后生成结构化收盘总结（大盘概况表 + 自选股表 + LLM 叙事）。
数据来源：
  1. akshare 原始指标（价格/涨跌幅/均线/成交量/振幅/换手率）
  2. 最近5日走势轨迹（日期+收盘价+涨跌幅）
LLM 负责叙事部分（市场特征 + 后市展望），表格部分由数据直接驱动。
"""
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

from scripts.stock_monitor.config import AppConfig
from scripts.stock_monitor.data_fetcher import (
    get_code_name_map,
    build_stock_snapshot,
    build_market_snapshot,
    get_all_index_data,
    get_realtime_quotes,
)
from scripts.stock_monitor.llm_client import call_with_fallback


# ============================================================
# LLM Prompts（仅用于叙事部分）
# ============================================================
MARKET_CHAR_SYSTEM_PROMPT = """你是一位资深的A股市场分析师。请根据提供的市场数据，用5-8个要点总结今日市场特征。

输出格式：每行一个要点，以"• "开头，不要编号。每个要点10-20字，简洁有力。

分析维度：
1. 情绪面：从指数涨跌幅度和量能判断市场整体情绪
2. 资金面：各指数成交额及环比变化、是否放量/缩量
3. 结构特征：权重vs小盘、成长vs价值、哪个板块强（从指数分化中判断）
4. 技术面：关键点位、均线支撑/压力
5. 如有明显异常（恐慌/亢奋/极端分化），单独指出

纯文本输出，不要用markdown格式。"""

OUTLOOK_SYSTEM_PROMPT = """你是一位专业的A股市场分析师。请根据今日市场数据，用3-4句话给出明日简要展望。

要求：
1. 结合今日涨跌、量能、情绪判断短期趋势
2. 指出需要关注的关键点位或信号
3. 语气客观中性，不做确定性预测
4. 纯文本输出，不要用markdown格式"""


# ============================================================
# 大盘概况表格数据
# ============================================================
def build_market_table() -> Dict[str, Any]:
    """构建大盘概况表格数据，纯数据驱动。"""
    indices = get_all_index_data()

    index_rows = []
    index_order = [
        ("sh000001", "上证指数"),
        ("sz399001", "深证成指"),
        ("sz399006", "创业板指"),
        ("sh000688", "科创50"),
        ("bj899050", "北证50"),
    ]

    for key, label in index_order:
        idx = indices.get(key, {})
        if not idx:
            continue
        amt = idx.get("amount")
        amt_chg = idx.get("amt_chg_pct")
        index_rows.append({
            "name": label,
            "close": idx.get("close"),
            "change_pct": idx.get("change_pct", 0),
            "amount": amt,  # 元
            "amount_chg_pct": amt_chg,  # 环比%
        })

    # 全市场成交额（上证+深证，近似全市场）
    sh_amt = indices.get("sh000001", {}).get("amount")
    sz_amt = indices.get("sz399001", {}).get("amount")
    total_amt = (sh_amt or 0) + (sz_amt or 0)

    # 成交额环比
    total_amt_chg = None
    sh_chg = indices.get("sh000001", {}).get("amt_chg_pct")
    sz_chg = indices.get("sz399001", {}).get("amt_chg_pct")
    if sh_chg is not None and sz_chg is not None:
        total_amt_chg = round((sh_chg + sz_chg) / 2, 2)

    return {
        "indices": index_rows,
        "total_amount": total_amt or None,
        "total_amount_chg_pct": total_amt_chg,
    }


# ============================================================
# 自选股表格数据
# ============================================================
def build_stock_table(config: AppConfig) -> List[Dict[str, Any]]:
    """构建自选股表现表格数据，数据驱动 + 均线关系。"""
    name_map = get_code_name_map()
    rows = []

    # 批量获取实时行情（一次 API 调用）
    rt_df = get_realtime_quotes(config.stocks)
    rt_map = {}
    if not rt_df.empty:
        for _, row in rt_df.iterrows():
            rt_map[row["代码"]] = {
                "成交额": row.get("成交额"),
                "换手率": row.get("换手率"),
                "振幅": row.get("振幅"),
            }

    for code in config.stocks:
        name = name_map.get(code, code)
        rt_data = rt_map.get(code)
        snapshot = build_stock_snapshot(code, name, rt_data=rt_data)
        if "error" in snapshot:
            rows.append({"code": code, "name": name, "error": snapshot["error"]})
            continue

        price = snapshot.get("price", {})
        change = snapshot.get("change", {})
        ma = snapshot.get("ma", {})

        # 均线关系描述
        ma_parts = []
        for ma_name in ["MA5", "MA10", "MA20"]:
            ma_data = ma.get(ma_name, {})
            if ma_data:
                ma_parts.append(f"{ma_name} {ma_data.get('relation', '')}")

        # 走势特征判断
        pct = change.get("pct", 0)
        amp = change.get("amplitude", 0) or 0
        if pct > 2:
            trend = "强势上涨" if amp > 5 else "稳步上涨"
        elif pct > 0:
            trend = "小幅上涨"
        elif pct > -1:
            trend = "窄幅震荡" if amp < 2 else "震荡整理"
        elif pct > -3:
            trend = "小幅下跌"
        else:
            trend = "明显下跌"

        rows.append({
            "code": code,
            "name": name,
            "close": price.get("close"),
            "change_pct": pct,
            "amount": snapshot.get("amount"),  # 成交额(元)
            "turnover": snapshot.get("turnover"),  # 换手率%
            "amplitude": amp,
            "ma_relation": " / ".join(ma_parts) if ma_parts else "数据不足",
            "trend": trend,
        })

    return rows


# ============================================================
# LLM 叙事部分
# ============================================================
def _build_market_char_prompt(market_table: dict) -> str:
    """构建市场特征分析的 LLM prompt。"""
    parts = ["以下是今日A股市场数据：", ""]

    # 指数数据
    parts.append("【三大指数】")
    for idx in market_table.get("indices", []):
        amt_str = f"成交额{_format_amount(idx.get('amount'))}"
        amt_chg = idx.get("amount_chg_pct")
        chg_str = f"量能环比{amt_chg:+.1f}%" if amt_chg is not None else ""
        parts.append(
            f"  {idx['name']}：收盘{idx['close']}，"
            f"涨跌{idx['change_pct']:+.2f}%，{amt_str}，{chg_str}"
        )

    # 全市场成交额
    total_amt = market_table.get("total_amount")
    total_amt_chg = market_table.get("total_amount_chg_pct")
    if total_amt:
        amt_str = _format_amount(total_amt)
        chg_str = f"（环比{total_amt_chg:+.1f}%）" if total_amt_chg is not None else ""
        parts.append(f"  全市场成交额（上证+深证）：{amt_str}{chg_str}")
    else:
        # 无全市场统计时，列出各指数成交额
        for idx in market_table.get("indices", [])[:3]:
            idx_amt = idx.get("amount")
            if idx_amt:
                parts.append(f"  {idx['name']}成交额：{_format_amount(idx_amt)}")

    parts.append(f"\n日期：{datetime.now().strftime('%Y-%m-%d')}")
    parts.append("\n请用5-8个要点总结今日市场特征。")
    return "\n".join(parts)


def _build_outlook_prompt(market_table: dict) -> str:
    """构建后市展望的 LLM prompt。"""
    parts = ["以下是今日A股市场收盘数据：", ""]
    for idx in market_table.get("indices", []):
        parts.append(
            f"{idx['name']}：收盘{idx['close']}，涨跌{idx['change_pct']:+.2f}%"
        )
    total_amt = market_table.get("total_amount")
    if total_amt:
        parts.append(f"全市场成交额（上证+深证）：{_format_amount(total_amt)}")
    parts.append(f"\n日期：{datetime.now().strftime('%Y-%m-%d')}")
    parts.append("\n请用3-4句话给出明日简要展望。")
    return "\n".join(parts)


def generate_market_characteristics(config: AppConfig, market_table: dict) -> str:
    """LLM 生成市场特征分析。"""
    user_prompt = _build_market_char_prompt(market_table)
    try:
        content, provider, log = call_with_fallback(
            config, MARKET_CHAR_SYSTEM_PROMPT, user_prompt, max_tokens=800, temperature=0.3,
        )
        print(f"[摘要] 市场特征 → {provider.name}")
        for line in log:
            print(line)
        return content.strip()
    except Exception as e:
        print(f"[摘要] 市场特征 LLM 调用失败: {e}")
        return _fallback_market_characteristics(market_table)


def generate_outlook(config: AppConfig, market_table: dict) -> str:
    """LLM 生成后市展望。"""
    user_prompt = _build_outlook_prompt(market_table)
    try:
        content, provider, log = call_with_fallback(
            config, OUTLOOK_SYSTEM_PROMPT, user_prompt, max_tokens=400, temperature=0.3,
        )
        print(f"[摘要] 后市展望 → {provider.name}")
        for line in log:
            print(line)
        return content.strip()
    except Exception as e:
        print(f"[摘要] 后市展望 LLM 调用失败: {e}")
        return "（展望需 LLM 支持，当前不可用）"


def _fallback_market_characteristics(market_table: dict) -> str:
    """LLM 不可用时的市场特征降级输出。"""
    total_amt = market_table.get("total_amount")
    parts = []
    for idx in market_table.get("indices", []):
        parts.append(f"• {idx['name']}：{idx['close']}（{idx['change_pct']:+.2f}%）成交额{_format_amount(idx.get('amount'))}")
    if total_amt:
        chg = market_table.get("total_amount_chg_pct")
        chg_str = f" 环比{chg:+.1f}%" if chg is not None else ""
        parts.append(f"• 全市场成交额（上证+深证）：{_format_amount(total_amt)}{chg_str}")
    return "\n".join(parts)


# ============================================================
# 完整收盘总结（结构化数据 + LLM 叙事）
# ============================================================
def generate_close_summary(config: AppConfig) -> Dict[str, Any]:
    """
    生成完整收盘总结，返回结构化 dict：
    {
        "market_table": {...},         # 大盘概况表格数据
        "market_characteristics": str, # LLM 市场特征叙事
        "stock_table": [...],          # 自选股表格数据
        "outlook": str,                # LLM 后市展望
    }
    """
    print("[摘要] 正在构建收盘总结...")

    # 1. 大盘概况（纯数据）
    market_table = build_market_table()
    print(f"[摘要] 大盘概况：{len(market_table.get('indices', []))}个指数，"
          f"总成交额{_format_amount(market_table.get('total_amount'))}")

    # 2. 自选股表现（纯数据）
    stock_table = build_stock_table(config)
    print(f"[摘要] 自选股表现：{len(stock_table)}只")

    # 3. 市场特征（LLM）
    market_characteristics = generate_market_characteristics(config, market_table)

    # 4. 后市展望（LLM）
    outlook = generate_outlook(config, market_table)

    return {
        "market_table": market_table,
        "market_characteristics": market_characteristics,
        "stock_table": stock_table,
        "outlook": outlook,
    }


# ============================================================
# 兼容旧接口
# ============================================================
def generate_market_summary(config: AppConfig) -> str:
    """兼容旧接口：生成市场整体走势摘要（纯文本）。"""
    market_table = build_market_table()
    return generate_market_characteristics(config, market_table)


def generate_stock_summary(config: AppConfig, code: str, name: str) -> str:
    """兼容旧接口：生成单只股票走势摘要。"""
    snapshot = build_stock_snapshot(code, name)
    if "error" in snapshot:
        return f"{name}({code})：{snapshot['error']}"

    price = snapshot.get("price", {})
    change = snapshot.get("change", {})
    ma = snapshot.get("ma", {})
    amount = snapshot.get("amount")

    parts = [f"{name}({code})：收盘{price.get('close')}，涨跌{change.get('pct', 0):+.2f}%"]
    if amount:
        parts.append(f"，成交额{_format_amount(amount)}")
    if ma:
        ma_strs = [f"{k}:{v.get('value')}({v.get('relation')})" for k, v in ma.items()]
        parts.append(f"，均线：{', '.join(ma_strs)}")
    return "".join(parts)


def generate_all_summaries(config: AppConfig) -> Dict[str, str]:
    """为所有自选股生成AI摘要。返回 {code: summary_str}。"""
    name_map = get_code_name_map()
    summaries: Dict[str, str] = {}
    for code in config.stocks:
        name = name_map.get(code, code)
        print(f"[摘要] 正在为 {name}({code}) 生成AI摘要...")
        summaries[code] = generate_stock_summary(config, code, name)
    return summaries


# ============================================================
# 工具函数
# ============================================================
def _format_amount(amount) -> str:
    """格式化成交额：元→亿。"""
    if amount is None:
        return "N/A"
    yi = amount / 1e8
    return f"{yi:.1f}亿"