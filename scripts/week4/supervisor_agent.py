"""
Week 4 · Day 1-2 — Supervisor 多 Agent 系统
=============================================
基于 Week 3 的单 Agent 架构扩展到 Supervisor 模式。

架构：
  入口 → 意图识别路由 → 分发给子 Agent → 结果聚合 → 综合输出

角色分工：
  Supervisor（本文件）— 调度中心，拆解任务、分发、汇总
  review_agent        — 风控专家：审客户信用、订单异常
  production_agent    — 排产专家：查物料、查设备、估交期

对比 Week 3 的单 Agent 结构：
  Week 3: 一个 Agent 同时做"查订单+查资源+综合判断"
  Week 4: 三个 Agent（Supervisor + 审核 + 生产），各司其职
              ↓ 优势：职责单一，Prompt 更专注，工具更聚焦
              ↓ 代价：需要额外的路由编排和结果聚合

知识块：⑧ Agent 集群 · ② Agent 核心机制 · ④ MCP
"""

import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# 加载 .env
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# 导入 Week 3 的 LLM 调用和工具
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts" / "week3"))
from langgraph_agent import call_llm, PROVIDERS, TOOLS

from agents.agent_router import AgentRouter
from agents.review_agent import review_order
from agents.production_agent import assess_production_feasibility
from auth.token_exchange import STS
from auth.audit_logger import AuditLogger


# ============================================================
# Supervisor System Prompt
# ============================================================
SUPERVISOR_PROMPT = """你是一个生产调度系统中的 Supervisor Agent。

你的职责是协调各子 Agent 完成综合调度决策。

## 子 Agent 能力

1. **审核 Agent** — 风控专家
   - 评价客户信用（等级/信用分/延期率）
   - 检测订单异常（交期异常、库存不足）
   - 输出：风险评级(高/中/低) + 原因

2. **生产 Agent** — 排产专家
   - 评估材料库存可行性
   - 评估设备负载
   - 输出：生产可行性报告

## 工作流程

1. 先调度审核 Agent 做风险评估
2. 同时调度生产 Agent 做产能评估
3. 综合两部分结果给出排产建议

## 输出要求
- 列出所有待处理订单
- 按优先级排序（风险×产能综合评估）
- 每单标注推荐操作和理由
"""


# ============================================================
# Supervisor 主逻辑
# ============================================================

class SupervisorAgent:
    """Supervisor Agent — 多 Agent 系统的调度中心。"""

    def __init__(self):
        self.router = AgentRouter()
        self.sts = STS()
        self.audit = AuditLogger()
        self.sub_agent_tokens: dict[str, str] = {}

    def _setup_auth(self, user_role: str = "scheduler") -> str:
        """初始化鉴权链路。"""
        user_token = self.sts.issue_user_token("user_001", user_role)
        self.audit.log("issue_token", "system", "STS", {"role": user_role}, "用户 Token 已签发")

        # 为每个子 Agent 交换受限 Token
        for agent_name, agent_role in [("review", "reviewer"), ("production", "scheduler")]:
            token, msg = self.sts.exchange(user_token, agent_role, self.audit.trace_id)
            if token:
                self.sub_agent_tokens[agent_name] = token
                self.audit.log("exchange_token", "STS", agent_name,
                               {"parent": user_token[:8], "role": agent_role}, msg)
            else:
                self.audit.log("exchange_token", "STS", agent_name, {}, f"失败：{msg}", "WARN")

        return user_token

    def dispatch_review(self, order_ids: list[str]) -> list[dict]:
        """调度审核 Agent。"""
        if "review" not in self.sub_agent_tokens:
            self.audit.log("dispatch", "supervisor", "review_agent", {}, "无权限", "ERROR")
            return []

        self.audit.log("dispatch", "supervisor", "review_agent", {"orders": order_ids}, "已调度")
        results = []
        for oid in order_ids:
            result = review_order(oid)
            results.append(result)
            self.audit.log("sub_call", "review_agent", oid, {}, f"完成，风险待评")
        return results

    def dispatch_production(self, order_ids: list[str] | None = None) -> dict:
        """调度生产 Agent。"""
        if "production" not in self.sub_agent_tokens:
            self.audit.log("dispatch", "supervisor", "production_agent", {}, "无权限", "ERROR")
            return {}

        self.audit.log("dispatch", "supervisor", "production_agent", {"orders": order_ids}, "已调度")
        result = assess_production_feasibility(order_ids)
        self.audit.log("sub_call", "production_agent", "feasibility", {}, "完成")
        return result

    def orchestrate(self, query: str) -> dict:
        """编排多 Agent 协作流程。"""
        print(f"\n{'='*60}")
        print(f" Supervisor 调度")
        print(f"{'='*60}")
        print(f" 请求：{query}")

        # --- 步骤 1：意图识别路由 ---
        route_result = self.router.route(query)
        print(f" 路由目标：{route_result['targets']}")

        # --- 步骤 2：鉴权初始化 ---
        user_token = self._setup_auth()
        print(f" 鉴权链路：已建立（Token: {user_token[:8]}...）")

        # --- 步骤 3：分发子 Agent ---
        # 模拟要审核的订单列表（实际应从订单查询中获取）
        sample_orders = ["ORD001", "ORD003", "ORD005"]

        review_results = []
        production_result = {}

        targets = route_result["targets"]

        if "review" in targets or "full" in targets:
            print(f"\n → 调度 [审核 Agent] 评估 {len(sample_orders)} 笔订单风险...")
            review_results = self.dispatch_review(sample_orders)

        if "production" in targets or "full" in targets:
            print(f"\n → 调度 [生产 Agent] 评估产能...")
            production_result = self.dispatch_production(sample_orders)

        if "query" in targets:
            print(f"\n → 直接查询（单 Agent 模式）")

        # --- 步骤 4：结果汇总 ---
        summary = {
            "query": query,
            "route": route_result,
            "review_results": review_results,
            "production_result": production_result,
            "audit_report": self.audit.get_report(),
        }

        # --- 步骤 5：综合输出 ---
        print(f"\n{'='*60}")
        print(f" 审核 Agent 发现")
        print(f"{'='*60}")
        for r in review_results:
            risk = json.loads(r.get("context", "{}"))
            print(f"  {r['order_id']}: 数据已采集（{r['status']}）")

        print(f"\n{'='*60}")
        print(f" 生产 Agent 发现")
        print(f"{'='*60}")
        print(f"  材料库存：{str(production_result.get('material', ''))[:100]}")
        print(f"  设备负载：{str(production_result.get('machine', ''))[:100]}")

        return summary


def main():
    """主入口。"""
    supervisor = SupervisorAgent()

    demo_queries = [
        "今天先做哪些订单？综合风险评估和产能情况给出排产建议",
        "ORD001 的订单风险评估一下，客户信用如何？",
        "帮我看看当前设备负载和材料库存情况",
    ]

    print("=" * 60)
    print("Week 4 — 多 Agent 集群（Supervisor 模式）")
    print("=" * 60)
    print(f"可用 Provider: {', '.join(p['name'] for p in PROVIDERS if p.get('enabled'))}")

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        supervisor.orchestrate(query)
        return

    print("\n📋 预设场景：\n")
    for i, s in enumerate(demo_queries, 1):
        print(f"  {i}. {s}")
    print()

    try:
        choice = input("选择场景编号（回车=全部演示）> ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = ""

    if choice.isdigit() and 1 <= int(choice) <= len(demo_queries):
        supervisor.orchestrate(demo_queries[int(choice) - 1])
    else:
        for i, s in enumerate(demo_queries, 1):
            print(f"\n{'#' * 60}")
            print(f"# 场景 {i}")
            print(f"{'#' * 60}")
            supervisor.orchestrate(s)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()