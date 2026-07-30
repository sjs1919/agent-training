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

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts" / "week3"))
from resource_server import query_inventory, query_machine_load
from langgraph_agent import call_llm


SYSTEM_PROMPT = """你是一位生产排产专家。你的职责是评估生产能力可行性。

## 输入数据
你会收到材料库存和设备负载的实时数据。

## 评估维度
1. 材料可行性：库存是否满足？采购周期是否允许？
2. 设备可行性：当前负载如何？哪台设备何时空闲？
3. 交期可行性：基于材料和设备，能否按时交付？

## 输出格式（JSON）
{
  "material_feasible": true,
  "machine_feasible": true,
  "delivery_feasible": true,
  "bottleneck": "瓶颈描述",
  "recommendation": "排产建议",
  "estimated_delay_days": 0
}
"""


def _parse_json(text: str) -> dict:
    """从 LLM 输出中解析 JSON（兼容 ```json``` 包裹和纯文本）。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


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
    """综合评估生产能力，调用 LLM 给出可行性判断。"""
    material = assess_material()
    machine = assess_machine_load()
    context = json.dumps({
        "material": material.get("data", ""),
        "machine": machine.get("data", ""),
        "orders_to_check": order_ids or [],
    }, ensure_ascii=False, indent=2)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"请评估以下订单的生产可行性。\n\n当前资源数据：\n{context}"},
    ]
    try:
        response = call_llm(messages)
        feasibility_data = _parse_json(response.choices[0].message.content)
    except Exception as e:
        feasibility_data = {"error": str(e)}
    return {
        "agent": "production_agent",
        "type": "feasibility_report",
        "material": material.get("data", ""),
        "machine": machine.get("data", ""),
        "orders_to_check": order_ids or [],
        "feasibility_assessment": feasibility_data,
    }