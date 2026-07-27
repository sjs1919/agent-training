"""
审核 Agent — 审核合同条款、客户信用、订单异常

角色定位：
  审核 Agent 是"风控专家"，负责评估每个订单的风险等级。
  它是多 Agent 系统中的子 Agent，由 Supervisor 调度。

职责：
  1. 客户信用评估 — 查客户等级、信用分、历史延期率
  2. 订单异常检测 — 交期是否合理、库存是否够、有无积压
  3. 风险评级 — 输出低/中/高危 + 原因

该 Agent 只读数据，不做排产决策。
"""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts" / "week3"))
from order_server import get_order_detail, get_production_status
from resource_server import query_customer

SYSTEM_PROMPT = """你是一位风控审核专家。你的职责是评估订单风险。

## 工作流程
收到订单评估请求后：
1. 查订单详情（get_order_detail）
2. 查客户信息（query_customer）
3. 查生产状态（get_production_status）
4. 综合判断风险等级

## 风险等级判断标准

### 高危（红色）- 必须报告
- 客户等级 C 或 D，或信用分 < 60
- 历史延期率 > 30%
- 订单交期已过
- 库存明确不足且采购周期 > 交期剩余天数

### 中危（黄色）- 需要关注
- 客户等级 B，信用分 60-75
- 历史延期率 15-30%
- 交期剩余 < 3 天
- 多个订单积压在同一设备

### 低危（绿色）- 正常放行
- 客户等级 S 或 A
- 信用分 > 75
- 历史延期率 < 15%
- 交期充裕

## 输出格式
使用 JSON 格式返回：
{
  "order_id": "ORD001",
  "risk_level": "high|medium|low",
  "risk_reasons": ["原因1", "原因2"],
  "credit_info": {"score": 85, "level": "A"},
  "anomalies": ["异常描述"]
}
"""


def build_review_context(order_id: str) -> str:
    """构建订单审核的上下文数据（JSON 格式）。"""
    try:
        detail = get_order_detail(order_id)
        production = get_production_status(order_id)
        detail_data = json.loads(detail) if detail else {}

        customer_name = detail_data.get("客户名", "")
        credit_data = {}
        if customer_name:
            credit_info = query_customer(customer_name=customer_name)
            try:
                credit_data = json.loads(credit_info)
            except (json.JSONDecodeError, TypeError):
                credit_data = {"raw": str(credit_info)}

        return json.dumps({
            "order_detail": detail_data,
            "production_status": production,
            "customer_credit": credit_data,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def review_order(order_id: str) -> dict:
    """审核单笔订单，返回风险评级结果。"""
    context = build_review_context(order_id)
    return {
        "order_id": order_id,
        "context": context,
        "agent": "review_agent",
        "status": "pending_review",
    }