"""
Week 3 · Day 2 — MCP Server: 订单服务（order_server）
======================================================
暴露 3 个工具：
  query_orders        — 按状态/客户查询订单列表
  get_order_detail    — 获取单个订单完整信息
  get_production_status — 获取订单当前生产环节

启动方式：
  python order_server.py                    # 直接运行
  mcp run scripts/week3/order_server.py     # 用 MCP CLI 启动

MCP Server 是什么？
  - 一个独立进程，通过标准输入输出（stdio）与外界通信
  - 遵循 MCP 协议（JSON-RPC 格式），向外暴露工具列表
  - 类比：微服务架构中的单个服务，通过 HTTP 暴露 API
  - 区别：MCP 不是 HTTP 协议，是 JSON-RPC over stdio/SSE

FastMCP 是什么？
  - MCP Python SDK 提供的高级封装，简化 Server 开发
  - 一个 @mcp.tool() 装饰器 = 注册一个工具
  - 框架自动处理协议细节（JSON-RPC 编解码、工具发现等）

知识块：④ MCP · ③ Tools/Skills
"""

import json

from mcp.server.fastmcp import FastMCP

from shared_data import load_orders, filter_by, format_table

# ---- 创建 MCP Server 实例 ----
# "order-server" 是 Server 名称，用于日志和调试
mcp = FastMCP("order-server")


def _orders_table(orders: list[dict]) -> str:
    """订单列表的专用表格格式，只显示最关键的列。"""
    return format_table(orders, ["id", "客户名", "产品", "数量", "交期", "当前环节", "状态"])


# ============================================================
# 工具 1：query_orders — 查询订单列表
# ============================================================
# @mcp.tool() 装饰器做了三件事：
#   1. 注册工具到 MCP Server
#   2. 把函数签名自动转换为 JSON Schema（参数名、类型、默认值）
#   3. 把 docstring 作为工具描述，LLM 根据它理解工具用途
#
# 注意：函数是同步的（不是 async），FastMCP 支持同步和异步
# ============================================================

@mcp.tool()
def query_orders(status: str = "", customer_name: str = "") -> str:
    """查询订单列表，可按状态和客户名筛选。

    Args:
        status: 订单状态筛选，如"生产中""紧急""待排产""排期中""即将完成"，空字符串=全部
        customer_name: 客户名模糊匹配，如"深圳精密五金"，空字符串=全部
    """
    # 1. 加载全部订单
    orders = load_orders()

    # 2. 按状态筛选（精确匹配）
    if status:
        orders = [o for o in orders if o["状态"] == status]

    # 3. 按客户名筛选（模糊匹配，in 操作符）
    if customer_name:
        orders = [o for o in orders if customer_name in o["客户名"]]

    # 4. 空结果处理
    if not orders:
        return "未找到匹配的订单。"

    # 5. 返回 Markdown 表格 + 计数
    return f"共 {len(orders)} 条订单：\n\n{_orders_table(orders)}"


# ============================================================
# 工具 2：get_order_detail — 获取单个订单详情
# ============================================================
# 返回 JSON 格式，包含所有字段，适合 LLM 做深度分析
# ============================================================

@mcp.tool()
def get_order_detail(order_id: str) -> str:
    """获取单个订单的完整信息。

    Args:
        order_id: 订单编号，如 ORD001
    """
    orders = load_orders()
    matched = filter_by(orders, id=order_id)
    if not matched:
        return f"未找到订单 {order_id}。"
    # JSON 缩进格式，方便 LLM 解析
    return json.dumps(matched[0], ensure_ascii=False, indent=2)


# ============================================================
# 工具 3：get_production_status — 获取生产环节
# ============================================================
# 返回简洁的文本描述，适合快速了解订单进度
# ============================================================

@mcp.tool()
def get_production_status(order_id: str) -> str:
    """获取订单的当前生产环节和状态。

    Args:
        order_id: 订单编号，如 ORD001
    """
    orders = load_orders()
    matched = filter_by(orders, id=order_id)
    if not matched:
        return f"未找到订单 {order_id}。"
    o = matched[0]
    return f"订单 {o['id']} — {o['产品']}\n  当前环节：{o['当前环节']}\n  状态：{o['状态']}\n  交期：{o['交期']}"


# ---- 启动入口 ----
# mcp.run(transport="stdio") 启动 stdio 传输层：
#   - 程序通过标准输入（stdin）接收 JSON-RPC 请求
#   - 通过标准输出（stdout）返回 JSON-RPC 响应
#   - 父进程（Agent）通过管道连接，实现进程间通信
# 这是最常用的 MCP 传输方式，适合本地工具
if __name__ == "__main__":
    mcp.run(transport="stdio")