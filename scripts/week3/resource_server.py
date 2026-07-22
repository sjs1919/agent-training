"""
Week 3 · Day 2 — MCP Server: 资源服务（resource_server）
========================================================
暴露 3 个工具：
  query_inventory    — 查询材料库存
  query_machine_load — 查询所有设备负载
  query_customer     — 获取客户信息（等级/信用/延期率）

与 order_server 的关系：
  - 两个 Server 独立运行，互不依赖
  - 共享同一个数据层（shared_data），但暴露不同视图
  - Agent 可以同时调用两个 Server 的工具
  - 类比：微服务架构中的两个独立服务，各有各的数据库视图

启动方式：
  python resource_server.py
  mcp run scripts/week3/resource_server.py

知识块：④ MCP · ③ Tools/Skills
"""

import json

from mcp.server.fastmcp import FastMCP

from shared_data import load_inventory, load_machines, load_customers, filter_by, format_table

# 创建 MCP Server 实例
mcp = FastMCP("resource-server")


# ============================================================
# 工具 1：query_inventory — 查询材料库存
# ============================================================
# 支持模糊搜索：输入"钛合金"可以匹配"TC4钛合金粉末"
# 返回全部材料时用表格格式，单种材料会返回 JSON 详情
# ============================================================

@mcp.tool()
def query_inventory(material_name: str = "") -> str:
    """查询材料库存，可按材料名模糊搜索。

    Args:
        material_name: 材料名关键词，如"钛合金""铝合金"，空字符串=全部
    """
    items = load_inventory()
    if material_name:
        # 模糊匹配：在"材料名"和"名称"两个字段中搜索
        items = [i for i in items if material_name in i["材料名"] or material_name in i["名称"]]
    if not items:
        return f"未找到匹配 {material_name} 的材料。"
    return f"共 {len(items)} 种材料：\n\n{format_table(items, ['名称', '材料名', '库存量', '单位', '安全库存', '采购周期天', '单价'])}"


# ============================================================
# 工具 2：query_machine_load — 查询设备负载
# ============================================================
# 无参数，返回所有设备的实时状态
# 自动统计运行中/空闲设备数量
# 这是 Agent 排产决策的关键依据：哪些设备有空，哪些在忙
# ============================================================

@mcp.tool()
def query_machine_load() -> str:
    """查询所有设备负载状态——哪些在运行、哪些空闲、预计何时释放。"""
    machines = load_machines()
    running = [m for m in machines if m["状态"] == "运行中"]
    idle = [m for m in machines if m["状态"] == "空闲"]
    return "\n".join([
        f"设备总数：{len(machines)} 台（运行中 {len(running)} / 空闲 {len(idle)}）\n",
        format_table(machines, ["machine_id", "型号", "类型", "当前订单", "预计空闲时间", "状态"]),
    ])


# ============================================================
# 工具 3：query_customer — 查询客户信息
# ============================================================
# 支持按编号精确查找或按名称模糊查找
# 单个结果返回 JSON 详情，多个结果返回表格
# 客户等级（S/A/B/C）直接影响排产优先级
# ============================================================

@mcp.tool()
def query_customer(customer_id: str = "", customer_name: str = "") -> str:
    """查询客户信息——等级、信用分、历史延期率、行业。

    Args:
        customer_id: 客户编号，如 C001
        customer_name: 客户名模糊匹配，如"深圳"
    """
    customers = load_customers()
    if customer_id:
        customers = filter_by(customers, id=customer_id)
    if customer_name:
        customers = [c for c in customers if customer_name in c["名称"]]
    if not customers:
        return "未找到匹配的客户。"
    if len(customers) == 1:
        return json.dumps(customers[0], ensure_ascii=False, indent=2)
    return f"共 {len(customers)} 个客户：\n\n{format_table(customers, ['id', '名称', '等级', '信用分', '历史延期率', '行业'])}"


# 启动 MCP Server
if __name__ == "__main__":
    mcp.run(transport="stdio")