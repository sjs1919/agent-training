"""
Week 3 · 共享数据层
====================
为 MCP Server 提供统一的数据加载接口。
两个 Server 共享同一份 CSV 数据，但暴露不同的工具视图。

设计思路：
  - 数据层与工具层分离：MCP Server 只负责暴露工具，数据加载逻辑集中管理
  - CSV 作为 Mock 数据源：生产环境替换为数据库即可，接口不变
  - 类比：Java 的 DAO 层，上层 Service 不关心数据来自哪里

数据文件：scripts/week3/data/
  orders.csv    — 15 条订单
  inventory.csv — 10 种材料
  machines.csv  — 8 台设备
  customers.csv — 5 个客户
"""

import csv
from pathlib import Path
from typing import Any

# ---- 数据目录 ----
# Path(__file__).parent 是当前文件所在目录（scripts/week3/）
# / "data" 拼接出 data/ 子目录
DATA_DIR = Path(__file__).parent / "data"


def _read_csv(filename: str) -> list[dict[str, str]]:
    """
    通用 CSV 读取函数。
    返回 list[dict] 格式，每个元素是一行数据，key 是列名，value 是单元格值。

    类比：Java 的 ResultSet → List<Map<String, String>>
    """
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        # csv.DictReader 自动用第一行作为列名，后续每行转为 dict
        return list(csv.DictReader(f))


# ---- 四个数据加载函数 ----
# 每个函数对应一个 CSV 文件，封装了数据源细节
# 上层调用方不需要知道数据来自 CSV 还是数据库

def load_orders() -> list[dict[str, str]]:
    """加载订单数据（15 条）。"""
    return _read_csv("orders.csv")


def load_inventory() -> list[dict[str, str]]:
    """加载库存数据（10 种材料）。"""
    return _read_csv("inventory.csv")


def load_machines() -> list[dict[str, str]]:
    """加载设备数据（8 台设备）。"""
    return _read_csv("machines.csv")


def load_customers() -> list[dict[str, str]]:
    """加载客户数据（5 个客户）。"""
    return _read_csv("customers.csv")


# ---- 工具函数 ----

def format_table(rows: list[dict], columns: list[str] | None = None) -> str:
    """
    将 dict 列表格式化为 Markdown 表格，方便 LLM 阅读。

    为什么用 Markdown 表格？
      - LLM 训练数据中包含大量 Markdown，解析效果好
      - 比 JSON 节省 token（无重复 key）
      - 人类也可读，方便调试

    示例输出：
      | id | 客户名 | 产品 | 数量 | 交期 |
      |---|---|---|---|---|
      | ORD001 | 深圳精密五金 | 手机中框支架 | 5000 | 2026-07-25 |
    """
    if not rows:
        return "（无数据）"
    # 用指定列或自动取第一行的 key
    cols = columns or list(rows[0].keys())
    # 表头行
    header = "| " + " | ".join(cols) + " |"
    # 分隔行（Markdown 表格语法）
    sep = "|" + "|".join(["---" for _ in cols]) + "|"
    lines = [header, sep]
    # 数据行
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(c, "")) for c in cols) + " |")
    return "\n".join(lines)


def filter_by(rows: list[dict], **kwargs: Any) -> list[dict]:
    """
    多条件 AND 过滤。
    值为 None 或空字符串的 key 自动跳过。

    示例：
      filter_by(orders, id="ORD001")           → 精确匹配 id
      filter_by(orders, status="生产中")        → 精确匹配状态
      filter_by(orders, id="ORD001", status="生产中")  → AND 过滤
    """
    result = rows
    for key, val in kwargs.items():
        if val is not None and val != "":
            # 用 strip() 做容错处理，去除前后空格
            result = [r for r in result if str(r.get(key, "")).strip() == str(val).strip()]
    return result