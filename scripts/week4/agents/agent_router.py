"""
意图识别路由 — 入口 Agent 分类用户请求并分发给对应子 Agent

核心逻辑：
  1. 接收原始用户请求
  2. 用 LLM 做意图分类（小模型判断即可）
  3. 根据分类路由到对应 Agent 或组合
  4. 返回路由决策

支持的路由目标：
  - "review"       → 审核 Agent（风险评估）
  - "production"   → 生产 Agent（产能评估）
  - "full"         → 先审核（数据来源）→ 再生产（可行性）→ Supervise（综合）
  - "query"        → 单 Agent 查数据（不需要协作）
"""

import json
from typing import Literal

RouteTarget = Literal["review", "production", "full", "query"]


class AgentRouter:
    """意图识别路由器。"""

    def __init__(self):
        self._routes = {
            "review": ["审核", "风险", "信用", "评级", "异常", "风控"],
            "production": ["设备", "材料", "库存", "负载", "产能", "生产", "机器"],
            "full": ["调度", "排产", "排序", "优先级", "今日", "先做哪些"],
        }

    def classify(self, query: str) -> list[RouteTarget]:
        """基于关键词对用户请求做意图分类。"""
        query_lower = query.lower()
        matched = []

        for route, keywords in self._routes.items():
            for kw in keywords:
                if kw in query_lower:
                    matched.append(route)
                    break

        # 优先匹配 full（包含调度/排产等综合意图）
        if "full" in matched:
            return ["full"]

        # 多个匹配时返回所有匹配的路由
        if matched:
            return matched

        # 默认走 query（单 Agent 查数据）
        return ["query"]

    def route(self, query: str, context: dict | None = None) -> dict:
        """路由决策：返回目标列表和上下文。"""
        targets = self.classify(query)
        return {
            "query": query,
            "targets": targets,
            "context": context or {},
        }