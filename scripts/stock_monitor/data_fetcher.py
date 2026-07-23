"""
数据获取模块：个股行情 + 历史K线 + 均线 + 多指数 + 全市场统计。
腾讯财经 API 用于个股实时行情和历史K线（东方财富 IP 被封）。
新浪数据源（akshare stock_zh_a_spot）用于全市场统计。
"""
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import akshare as ak
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================================
# 持久 Session
# ============================================================
_SESSION: requests.Session | None = None


def _get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
        })
        retry_strategy = Retry(
            total=3, backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(
            pool_connections=10, pool_maxsize=10,
            max_retries=retry_strategy, pool_block=False,
        )
        _SESSION.mount("http://", adapter)
        _SESSION.mount("https://", adapter)
    return _SESSION


def _rate_limit():
    time.sleep(random.uniform(0.15, 0.4))


# ============================================================
# 代码→名称映射（akshare，上交所/深交所接口，不受 IP 封影响）
# ============================================================
_CODE_NAME_CACHE: Optional[Dict[str, str]] = None


def get_code_name_map() -> Dict[str, str]:
    global _CODE_NAME_CACHE
    if _CODE_NAME_CACHE is None:
        df = ak.stock_info_a_code_name()
        _CODE_NAME_CACHE = dict(zip(df["code"], df["name"]))
    return _CODE_NAME_CACHE


def _qq_code(code: str) -> str:
    return f"sh{code}" if code.startswith("6") else f"sz{code}"


# ============================================================
# 腾讯实时行情字段解析
# 个股: v_sh600584="1~名称~600584~price~昨收~今开~成交量~..."
# 指数(sqt): 同格式，字段 3=price, 4=昨收, 5=今开, 6=成交量(手),
#            31=涨跌额, 32=涨跌幅%, 33=最高, 34=最低, 37=成交额(万元)
# ============================================================
_QQ_FIELDS = {
    1: "名称", 3: "最新价", 4: "昨收", 5: "今开",
    6: "成交量", 31: "涨跌额", 32: "涨跌幅",
    33: "最高", 34: "最低", 37: "成交额", 43: "振幅", 38: "换手率",
}


def _parse_qq(text: str) -> Optional[dict]:
    try:
        inner = text.split('"')[1] if '"' in text else text.split("=")[1]
        parts = inner.split("~")
        return {name: parts[idx] if idx < len(parts) else None
                for idx, name in _QQ_FIELDS.items()}
    except (IndexError, ValueError):
        return None


# ============================================================
# 个股实时行情（腾讯 API）
# ============================================================
def get_realtime_quotes(codes: List[str]) -> pd.DataFrame:
    session = _get_session()
    name_map = get_code_name_map()
    qq_codes = [_qq_code(c) for c in codes]
    rows = []

    url = "https://qt.gtimg.cn/q=" + ",".join(qq_codes)
    _rate_limit()

    try:
        r = session.get(url, timeout=10)
        r.raise_for_status()
        lines = r.text.strip().split("\n")
        for line, code in zip(lines, codes):
            p = _parse_qq(line)
            if not p:
                continue
            amt_wan = _sf(p.get("成交额"))
            rows.append({
                "代码": code,
                "名称": p.get("名称", name_map.get(code, code)),
                "最新价": _sf(p.get("最新价")),
                "涨跌幅": _sf(p.get("涨跌幅")),
                "涨跌额": _sf(p.get("涨跌额")),
                "今开": _sf(p.get("今开")),
                "最高": _sf(p.get("最高")),
                "最低": _sf(p.get("最低")),
                "昨收": _sf(p.get("昨收")),
                "成交量": _sf(p.get("成交量")),
                "成交额": amt_wan * 10000 if amt_wan else None,  # 万→元
                "换手率": _sf(p.get("换手率")),
                "振幅": _sf(p.get("振幅")),
            })
    except Exception as e:
        print(f"[数据] 获取实时行情失败: {e}")

    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ============================================================
# 个股历史K线 + 均线（腾讯 K 线 API）
# ============================================================
_KLINE_COLS = ["日期", "开盘", "收盘", "最高", "最低", "成交量"]


def get_hist_data(code: str, days: int = 30) -> pd.DataFrame:
    session = _get_session()
    qq = _qq_code(code)
    _rate_limit()

    try:
        r = session.get(
            "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
            params={"param": f"{qq},day,,,{days + 10},qfq"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 0:
            return pd.DataFrame()

        stock_data = data.get("data", {}).get(qq, {})
        klines = stock_data.get("qfqday", []) or stock_data.get("day", [])
        if not klines:
            return pd.DataFrame()

        rows = [{c: r[i] if i < len(r) else None for i, c in enumerate(_KLINE_COLS)}
                for r in klines if len(r) >= 6]
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df["日期"] = pd.to_datetime(df["日期"], errors="coerce").dt.date
        for col in ["开盘", "收盘", "最高", "最低", "成交量"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.sort_values("日期").reset_index(drop=True)
        df["涨跌幅"] = df["收盘"].pct_change() * 100
        df["振幅"] = ((df["最高"] - df["最低"]) / df["收盘"].shift(1)) * 100
        df["成交额"] = df["成交量"] * 100 * df["收盘"]  # 估算：成交量(手) * 100(股/手) * 收盘价(元)

        for w in [5, 10, 20]:
            df[f"MA{w}"] = df["收盘"].rolling(window=w).mean()

        return df
    except Exception as e:
        print(f"[数据] 获取 {code} 历史K线失败: {e}")
        return pd.DataFrame()


def get_latest_ma_values(code: str) -> Dict[str, Optional[float]]:
    df = get_hist_data(code, days=30)
    if df.empty or len(df) < 20:
        return {"MA5": None, "MA10": None, "MA20": None}
    latest = df.iloc[-1]
    return {"MA5": latest.get("MA5"), "MA10": latest.get("MA10"), "MA20": latest.get("MA20")}


# ============================================================
# 四大指数数据（腾讯 sqt 端点，含昨收等环比所需字段）
# ============================================================
_INDEX_MAP = {
    "sh000001": "上证指数",
    "sz399001": "深证成指",
    "sz399006": "创业板指",
    "sh000688": "科创50",
    "bj899050": "北证50",
    "sh000985": "中证全指",  # 近似全A
}

# 全市场统计缓存（收盘前不重复拉）
_MARKET_BREADTH_CACHE: Optional[dict] = None
_MARKET_BREADTH_DATE: Optional[str] = None

# 持久化目录
import os as _os
_STATS_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "data")
_os.makedirs(_STATS_DIR, exist_ok=True)

# 昨日指数数据持久化文件（用于环比计算，K线API没有成交额字段）
_INDEX_STATS_FILE = _os.path.join(_STATS_DIR, "index_stats_yesterday.json")


def _load_yesterday_indices() -> Optional[dict]:
    """加载昨日保存的指数数据。"""
    import json as _json
    try:
        with open(_INDEX_STATS_FILE, "r", encoding="utf-8") as f:
            data = _json.load(f)
        if data.get("date") == (datetime.now() - timedelta(days=1)).strftime("%Y%m%d"):
            return data.get("indices", {})
    except Exception:
        pass
    return None


def _save_today_indices(indices: dict):
    """保存今日指数数据供明天环比使用。"""
    import json as _json
    try:
        to_save = {
            "date": datetime.now().strftime("%Y%m%d"),
            "indices": {
                sym: {"volume": d.get("volume"), "amount": d.get("amount")}
                for sym, d in indices.items()
            },
        }
        with open(_INDEX_STATS_FILE, "w", encoding="utf-8") as f:
            _json.dump(to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[数据] 保存指数数据失败: {e}")


def get_all_index_data() -> dict:
    """
    获取四大指数数据，含成交量和环比。
    环比通过持久化昨日数据实现（K线API无成交额）。
    返回: {sh000001: {name, close, change_pct, volume, amount, vol_chg_pct, amt_chg_pct}, ...}
    """
    # 批量请求 sqt（一次返回全部四个指数）
    session = _get_session()
    symbols = list(_INDEX_MAP.keys())
    url = "https://web.sqt.gtimg.cn/q=" + ",".join(symbols)
    _rate_limit()

    result = {}
    try:
        r = session.get(url, timeout=10)
        r.raise_for_status()
        lines = r.text.strip().split("\n")

        for line, sym in zip(lines, symbols):
            p = _parse_qq(line)
            if not p:
                continue
            amt_wan = _sf(p.get("成交额"))
            vol = _sf(p.get("成交量"))
            result[sym] = {
                "name": _INDEX_MAP.get(sym, sym),
                "close": _sf(p.get("最新价")),
                "prev_close": _sf(p.get("昨收")),
                "open": _sf(p.get("今开")),
                "high": _sf(p.get("最高")),
                "low": _sf(p.get("最低")),
                "change_pct": _sf(p.get("涨跌幅")) or 0,
                "volume": vol,
                "amount": (amt_wan * 10000) if amt_wan else None,
            }

        # --- 环比：从昨日持久化数据计算 ---
        yesterday_indices = _load_yesterday_indices()
        if yesterday_indices:
            for sym, data in result.items():
                yest = yesterday_indices.get(sym, {})
                vol = data.get("volume")
                amt = data.get("amount")
                yvol = yest.get("volume")
                yamt = yest.get("amount")
                if vol and yvol and yvol > 0:
                    data["vol_chg_pct"] = round((vol / yvol - 1) * 100, 2)
                if amt and yamt and yamt > 0:
                    data["amt_chg_pct"] = round((amt / yamt - 1) * 100, 2)

        # 保存今日数据供明天对比
        _save_today_indices(result)

    except Exception as e:
        print(f"[数据] 获取指数批量数据失败: {e}")

    return result


# 昨日全市场统计持久化文件（用于环比计算）
_MARKET_STATS_FILE = _os.path.join(_STATS_DIR, "market_stats_yesterday.json")


def _load_yesterday_stats() -> Optional[dict]:
    """加载昨日保存的全市场统计。"""
    import json as _json
    try:
        with open(_MARKET_STATS_FILE, "r", encoding="utf-8") as f:
            data = _json.load(f)
        if data.get("date") == (datetime.now() - timedelta(days=1)).strftime("%Y%m%d"):
            return data
    except Exception:
        pass
    return None


def _save_today_stats(result: dict):
    """保存今日全市场统计供明天环比使用。"""
    import json as _json
    try:
        to_save = {
            "date": datetime.now().strftime("%Y%m%d"),
            "total_amount": result.get("total_amount"),
            "total_volume": result.get("total_volume"),
            "up": result.get("up"),
            "down": result.get("down"),
            "flat": result.get("flat"),
            "total": result.get("total"),
            "median_pct": result.get("median_pct"),
        }
        with open(_MARKET_STATS_FILE, "w", encoding="utf-8") as f:
            _json.dump(to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[数据] 保存市场统计失败: {e}")


def get_market_stats() -> dict:
    """
    获取全市场统计：涨跌家数、中位数涨跌幅、总成交额/成交量及其环比。
    使用 akshare stock_zh_a_spot（新浪数据源，不经过东方财富）。
    每天只拉一次（缓存到日期变更）。
    """
    global _MARKET_BREADTH_CACHE, _MARKET_BREADTH_DATE
    today = datetime.now().strftime("%Y%m%d")

    if _MARKET_BREADTH_CACHE is not None and _MARKET_BREADTH_DATE == today:
        return _MARKET_BREADTH_CACHE

    try:
        print("[数据] 正在获取全市场统计（新浪数据源，约15秒）...")
        df = ak.stock_zh_a_spot()
        if df.empty or "涨跌幅" not in df.columns:
            return {}

        pcts = pd.to_numeric(df["涨跌幅"], errors="coerce").dropna()

        result = {
            "up": int((pcts > 0).sum()),
            "down": int((pcts < 0).sum()),
            "flat": int((pcts == 0).sum()),
            "total": len(pcts),
            "median_pct": round(float(pcts.median()), 2),
            "avg_pct": round(float(pcts.mean()), 2),
        }

        # 总成交额（如果有该列）
        if "成交额" in df.columns:
            amts = pd.to_numeric(df["成交额"], errors="coerce").dropna()
            if len(amts) > 0:
                result["total_amount"] = float(amts.sum())

        # 总成交量
        if "成交量" in df.columns:
            vols = pd.to_numeric(df["成交量"], errors="coerce").dropna()
            if len(vols) > 0:
                result["total_volume"] = float(vols.sum())

        # --- 环比：加载昨日数据计算 ---
        yesterday = _load_yesterday_stats()
        if yesterday:
            y_amt = yesterday.get("total_amount")
            t_amt = result.get("total_amount")
            if y_amt and t_amt and y_amt > 0:
                result["total_amount_chg_pct"] = round((t_amt / y_amt - 1) * 100, 2)
            y_vol = yesterday.get("total_volume")
            t_vol = result.get("total_volume")
            if y_vol and t_vol and y_vol > 0:
                result["total_volume_chg_pct"] = round((t_vol / y_vol - 1) * 100, 2)
            y_median = yesterday.get("median_pct")
            t_median = result.get("median_pct")
            if y_median is not None and t_median is not None:
                result["median_chg"] = round(t_median - y_median, 2)  # 绝对变化

        # 保存今日数据供明天对比
        _save_today_stats(result)

        _MARKET_BREADTH_CACHE = result
        _MARKET_BREADTH_DATE = today
        print(f"[数据] 全市场统计: 上涨{result['up']} 下跌{result['down']} "
              f"中位数{result['median_pct']}% 总成交额{result.get('total_amount', 'N/A')}")
        return result

    except Exception as e:
        print(f"[数据] 获取全市场统计失败: {e}")
        return {}


# ============================================================
# 个股快照（供 LLM 摘要）
# ============================================================
def _get_realtime_single(code: str) -> dict:
    """获取单只股票实时数据（成交额/换手率/振幅），失败返回空 dict。"""
    try:
        df = get_realtime_quotes([code])
        if df.empty:
            return {}
        row = df.iloc[0]
        return {
            "成交额": row.get("成交额"),
            "换手率": row.get("换手率"),
            "振幅": row.get("振幅"),
        }
    except Exception:
        return {}


def build_stock_snapshot(code: str, name: str, rt_data: Optional[dict] = None) -> dict:
    try:
        df = get_hist_data(code, days=25)
        if df.empty or len(df) < 5:
            return {"code": code, "name": name, "error": "数据不足"}

        today = df.iloc[-1]
        yesterday = df.iloc[-2]

        # 实时行情数据（用于获取准确的成交额/换手率/振幅）
        if rt_data is None:
            rt_data = _get_realtime_single(code)

        snapshot = {
            "code": code, "name": name,
            "date": str(today.get("日期", "")),
            "price": {
                "open": _fn(today.get("开盘")), "close": _fn(today.get("收盘")),
                "high": _fn(today.get("最高")), "low": _fn(today.get("最低")),
                "prev_close": _fn(yesterday.get("收盘")),
            },
            "change": {
                "pct": _fz(today.get("涨跌幅")),
                "amplitude": rt_data.get("振幅") or _fz(today.get("振幅")),
            },
            "volume": {
                "today": _fz(today.get("成交量")),
                "yesterday": _fz(yesterday.get("成交量")),
            },
            "amount": rt_data.get("成交额") or _fz(today.get("成交额")),
            "turnover": rt_data.get("换手率"),
            "ma": {},
        }
        for ma in ["MA5", "MA10", "MA20"]:
            ma_val = today.get(ma)
            if pd.notna(ma_val) and ma_val is not None:
                snapshot["ma"][ma] = {
                    "value": round(float(ma_val), 2),
                    "relation": "上方" if today["收盘"] > ma_val else "下方",
                }

        recent = df.tail(5)
        snapshot["trajectory"] = [
            {"date": str(r["日期"]), "close": _fn(r["收盘"]), "change_pct": _fz(r.get("涨跌幅"))}
            for _, r in recent.iterrows()
        ]
        return snapshot
    except Exception as e:
        return {"code": code, "name": name, "error": str(e)}


def build_market_snapshot() -> dict:
    indices = get_all_index_data()
    breadth = get_market_stats()
    return {"indices": indices, "breadth": breadth}


# ============================================================
# 工具函数
# ============================================================
def _sf(val) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _fn(val) -> Optional[float]:
    return _sf(val)


def _fz(val) -> float:
    return _sf(val) or 0.0
