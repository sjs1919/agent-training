# 第四周 Day1+2 — 多 Agent 协作模式 + 子 Agent 设计

> **本周一句话**：Week 3 是一个 Agent 掌握所有能力，Week 4 是多个专业 Agent 各司其职，由 Supervisor 统一调度。

---

## Day 1：多 Agent 协作模式

### 1. 为什么需要多 Agent？

回顾 week3 的工作方式：**一个 Agent 包揽所有**——调度、查订单、查库存、查设备、查客户，全在一个 Prompt 里：

```python
# week3 方式：一个 Prompt 定义所有能力和规则
SYSTEM_PROMPT = """
你是 3D 打印/CNC 加工生产调度专家。
你拥有：订单工具（query_orders...）、资源工具（query_inventory...）
调度规则：交期紧 > 客户等级高 > 信用分高...
"""
```

**问题**：

| 问题 | 单 Agent 的表现 | 多 Agent 如何解决 |
|------|-----------------|-------------------|
| **Prompt 膨胀** | 工具/规则越多，Prompt 越长，LLM 决策准确率下降 | 每个子 Agent 只有 2-3 个工具，Prompt 精炼 |
| **职责混杂** | 查订单和审信用的逻辑放在同一个决策循环里 | 审核只做风控，生产只看产能 |
| **扩展困难** | 新增能力 = 改大已有 Prompt，容易影响现有能力 | 新增能力 = 加一个子 Agent，不影响现有 |
| **安全风险** | Agent 什么数据都能看（客户信息/订单/库存） | 每个子 Agent 只有对应权限 |

### 2. 解决方案：Supervisor 模式

**核心思路**：一个主 Agent（Supervisor）负责任务拆解和分发，多个子 Agent（Worker）各司其职。

```
         Supervisor（调度中心）
               │
        ┌──────┴──────┐
        │              │
   审核 Agent      生产 Agent
   (风控专家)      (排产专家)
        │              │
   只看客户信用    只看物料/设备
   和订单异常     和交期可行性
```

**三个关键设计原则**：

| 原则 | 说明 |
|------|------|
| **Supervisor 不做具体业务** | 只负责拆解、分发、汇总。不直接调工具，不参与业务判断 |
| **子 Agent 各司其职** | 每个子 Agent 的 Prompt 只覆盖自己负责的领域，工具也只限该领域 |
| **子 Agent 之间不直接通信** | 所有协调走 Supervisor，避免耦合 |

### 3. 意图识别路由

**核心问题**：Supervisor 收到用户请求后，怎么知道该交给哪个子 Agent？

**三种路由方式**：

| 方式 | 实现 | 优点 | 缺点 |
|------|------|------|------|
| **关键词路由** | 预定义关键词→Agent 映射表 | 简单、确定、零成本 | 不支持复杂意图 |
| **LLM 路由** | 小模型做意图分类 | 灵活、支持模糊意图 | 有成本、有延迟 |
| **混合路由** | 关键词兜底 + LLM 决策 | 平衡性能和灵活性 | 实现稍复杂 |

**我们的实现（关键词路由）**：

```python
class AgentRouter:
    _routes = {
        "review":    ["审核", "风险", "信用", "评级", "异常","风控"],
        "production":["设备", "材料", "库存", "负载", "产能", "生产","机器"],
        "full":      ["调度", "排产", "排序", "优先级", "今日", "先做哪些"],
    }

    def classify(self, query: str) -> list[str]:
        matched = []
        for route, keywords in self._routes.items():
            for kw in keywords:
                if kw in query.lower():
                    matched.append(route)
                    break
        return matched or ["query"]  # 默认走单 Agent 查询
```

### 4. 子 Agent 生命周期管理

| 阶段 | 操作 | 说明 |
|------|------|------|
| **创建** | Supervisor 按需调度 | 懒加载，需要时才创建 |
| **执行** | 子 Agent 独立调用工具 | 不干扰其他子 Agent |
| **返回** | 结果回传给 Supervisor | 只传摘要，不传原始数据 |
| **销毁** | 超时自动销毁 | 防止资源泄漏 |

### 5. 对比

```
week3（单 Agent）                     week4（多 Agent Supervisor）
─────────────────────────              ─────────────────────────
1 个 Prompt 管所有事                   每个子 Agent 1 个 Prompt
6 个工具堆在一起                       每个子 Agent 2-3 个工具
加能力 = 改大 Prompt                   加能力 = 新增子 Agent
无鉴权                                Token Exchange + RBAC
无审计                                全链路审计日志
调试看一条 messages 链                 每个子 Agent 独立可测试
```

---

## Day 2：子 Agent 设计

### 1. 审核 Agent（review_agent）

**角色定位**：风控专家。评估订单的客户信用和异常风险。

**Prompt 设计**：

```
你是一位风控审核专家。你的职责是评估订单风险。

风险等级判断标准：
  高危（红色）：客户等级 C/D，信用分 < 60，历史延期率 > 30%
  中危（黄色）：客户等级 B，信用分 60-75，延期率 15-30%
  低危（绿色）：客户等级 S/A，信用分 > 75，延期率 < 15%
```

**工具**（从 Week 3 复用）：
- `get_order_detail(order_id)` — 订单详情
- `get_production_status(order_id)` — 生产环节
- `query_customer(customer_name)` — 客户信用

### 2. 生产 Agent（production_agent）

**角色定位**：排产专家。评估物料和设备可行性。

**Prompt 设计**（当前在代码中由函数直接返回数据，未来可升级为 LLM 驱动）：

```
你是一位排产专家。根据物料库存和设备负载，判断能否按时交付。
```

**工具**（从 Week 3 复用）：
- `query_inventory(material_name)` — 材料库存
- `query_machine_load()` — 设备负载

### 3. Supervisor 调度流程

```
① 路由：AgentRouter.classify(query)
   例如 "今天先做哪些订单？" → ["full"] → 全部调度

② 鉴权：STS.issue_user_token() + STS.exchange()
   为每个子 Agent 签发受限 Token

③ 分发：
   dispatch_review(["ORD001", "ORD003", ...])
   dispatch_production(["ORD001", "ORD003", ...])

④ 汇总：综合两个子 Agent 的结果
```

### 4. 代码理解脉络

```
第 1 步（10min）→ agents/agent_router.py
   理解关键词路由的实现
   关键问题：如果用户说"帮我看看信用的风险"，路由会匹配到哪个 Agent？

第 2 步（15min）→ agents/review_agent.py
   理解审核 Agent 的风险评级逻辑
   关键问题：review_order() 返回的结构里，risk_level 有哪些取值？

第 3 步（10min）→ agents/production_agent.py
   理解生产 Agent 的产能评估逻辑
   关键问题：assess_production_feasibility() 会调用哪些工具？

第 4 步（20min）→ supervisor_agent.py（重点）
   理解 Supervisor 的四步编排流程
   关键问题：supervisor_agent.py:45-51 的 _setup_auth 在做什么？
```

---

## 核心认知（今天最重要的 3 句话）

1. **多 Agent 不是为了炫技，是为了职责分离** — 当你的 Agent 开始做多件不相关的事情时，就该拆了
2. **Supervisor 不做具体业务** — 它是指挥官，不是士兵。指令拆解→分发→汇总，不直接调工具
3. **子 Agent 之间不通信** — 所有协调走 Supervisor，这是解耦的关键

---

## 参考资料

| 知识块 | 资料 |
|--------|------|
| ⑧ Agent 集群 | [LangGraph Multi-Agent 文档](https://langchain-ai.github.io/langgraph/concepts/multi_agent/) ⭐ · [《智能体设计模式》中文版 — Jimmy Song](https://jimmysong.io/zh/book/agentic-design-patterns/) ⭐