"""
生产 Agent — 查物料、查机器、估交期可行性

角色定位：
  生产 Agent 是"排产专家"，负责评估生产能力可行性。
  它是多 Agent 系统中的子 Agent，由 Supervisor 调度。

职责：
  1. 材料可行性 — 库存够不够？采购周期多长？
  2. 设备可行性 — 设备负载如何？预计空闲时间？
  3. 交期可行性 — 基于材料和设备估算能否按时交付
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts" / "week3"))
from resource_server import query_inventory, query_machine_load


def assess_material(codes: list[str] | None = None) -> dict:
    """评估材料可行性。"""
    inv = query_inventory()
    return {
        "agent": "production_agent",
        "type": "material_assessment",
        "data": inv,
    }


def assess_machine_load() -> dict:
    """评估设备负载。"""
    load = query_machine_load()
    return {
        "agent": "production_agent",
        "type": "machine_assessment",
        "data": load,
    }


def assess_production_feasibility(order_ids: list[str] = None) -> dict:
    """综合评估生产能力。"""
    material = assess_material()
    machine = assess_machine_load()
    return {
        "agent": "production_agent",
        "type": "feasibility_report",
        "material": material.get("data", ""),
        "machine": machine.get("data", ""),
        "orders_to_check": order_ids or [],
    }