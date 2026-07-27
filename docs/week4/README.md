# Week 4 — 多 Agent 集群 + 鉴权体系

> **2026-07-27 ~ 07-31** | 知识块 ⑧ ⑨
> 本周一句话：一个 Agent 不够用，让多个 Agent 协作并管好权限。

## 产出

```
scripts/week4/
├── supervisor_agent.py         # Supervisor 主调度（编排多 Agent 协作）
├── agents/
│   ├── agent_router.py         # 意图识别路由器（关键词分类→分发）
│   ├── review_agent.py         # 审核 Agent（客户信用+风险评级）
│   └── production_agent.py    # 生产 Agent（物料+设备+交期可行性）
└── auth/
    ├── token_exchange.py       # Token Exchange 鉴权（RFC 8693）+ RBAC 权限矩阵
    └── audit_logger.py         # 结构化审计日志（Trace ID 全链路串联）
```

## 架构

```
用户请求
    │
    ▼
┌─────────────────────┐
│  Supervisor Agent   │  ← 调度中心
│  (意图识别+分发+汇总) │
└────┬──────────┬─────┘
     │          │
     ▼          ▼
┌────────┐ ┌────────┐
│ 审核    │ │ 生产    │  ← 子 Agent，各司其职
│ Agent  │ │ Agent  │
└────────┘ └────────┘
     │          │
     ▼          ▼
┌─────────────────────┐
│  鉴权层 (STS+RBAC)   │  ← Token Exchange 权限控制
└─────────────────────┘
     │
     ▼
┌─────────────────────┐
│  审计日志 (Trace ID)  │  ← 全链路不可否认记录
└─────────────────────┘
```

## 运行

```bash
cd scripts/week4

# Supervisor 模式（多 Agent 协作）
python supervisor_agent.py
```

## 对比 Week 3

| 维度 | Week 3（单 Agent） | Week 4（多 Agent Supervisor） |
|------|-------------------|-------------------------------|
| Prompt 复杂度 | 高（一个 Prompt 覆盖所有能力） | 低（每个 Agent 只做一件事） |
| 工具数量 | 6 个（混杂在一起） | 每个子 Agent 2-3 个 |
| 扩展性 | 加能力 = 改大 Prompt | 加能力 = 新增子 Agent |
| 鉴权 | 无 | Token Exchange + RBAC |
| 审计 | 无 | Trace ID 全链路日志 |

## 每日要点

### Day 1 — 多 Agent 协作模式
- Supervisor/Manager-Worker 模式原理
- 意图识别路由策略（关键词路由 / LLM 路由 / 混合路由）
- 子 Agent 生命周期管理（创建/挂起/销毁）
- **配套代码**：`agents/agent_router.py` + `supervisor_agent.py`（路由+分发）

### Day 2 — 子 Agent 设计
- 审核 Agent：客户信用评估 + 订单异常检测 + 风险评级
- 生产 Agent：材料可行性 + 设备负载 + 交期可行性
- 结果聚合：Supervisor 汇总多 Agent 输出
- **配套代码**：`agents/review_agent.py` + `agents/production_agent.py`

### Day 3 — 鉴权体系
- Token Exchange（RFC 8693）：父 Token → 受限子 Token 转换
- 洋葱型防御模型（网关→运行时→工具三层）
- RBAC 权限矩阵：5 角色，每角色可调用不同工具
- **配套代码**：`auth/token_exchange.py`

### Day 4 — 审计日志 + 联调
- 结构化审计日志（主体/时间/操作/结果）
- Trace ID 全链路串联
- 多 Agent + 鉴权完整联调
- **配套代码**：`auth/audit_logger.py`

## 模块职责

### supervisor_agent.py — Supervisor 调度中心

**职责**：编排多 Agent 协作流程：意图路由 → 鉴权初始化 → 分发子 Agent → 结果汇总。

**对外接口**：
| 函数/类 | 说明 |
|---------|------|
| `SupervisorAgent.orchestrate(query)` | 全流程编排（路由→鉴权→分发→汇总） |

### agents/agent_router.py — 意图识别路由

**职责**：根据用户请求的关键词，决定路由到哪个子 Agent。

**对外接口**：
| 方法 | 说明 |
|------|------|
| `AgentRouter.classify(query)` | 关键词匹配，返回路由目标列表 |
| `AgentRouter.route(query, context)` | 路由决策：返回目标列表 + 上下文 |

### agents/review_agent.py — 审核 Agent

**职责**：评估订单风险等级（高危/中危/低危）。

**对外接口**：
| 函数 | 说明 |
|------|------|
| `review_order(order_id)` | 审核单笔订单，返回风险评级 |

### agents/production_agent.py — 生产 Agent

**职责**：评估生产能力可行性（材料+设备+交期）。

**对外接口**：
| 函数 | 说明 |
|------|------|
| `assess_production_feasibility(order_ids)` | 综合评估生产可行性 |

### auth/token_exchange.py — 鉴权体系

**职责**：Token Exchange（RFC 8693）+ RBAC 权限矩阵。

**对外接口**：
| 类/方法 | 说明 |
|---------|------|
| `STS.issue_user_token(user_id, role)` | 签发用户 Token |
| `STS.exchange(token, target_role)` | Token Exchange：权限收缩 |
| `STS.validate(token, tool)` | 验证 Token 是否有权调用工具 |
| `STS.revoke_all()` | 一键吊销所有 Token |

### auth/audit_logger.py — 审计日志

**职责**：记录 Agent 调用链路的完整审计信息。

**对外接口**：
| 方法 | 说明 |
|------|------|
| `AuditLogger.log(action, subject, target, ...)` | 记录一条审计日志 |
| `AuditLogger.get_report()` | 生成审计报告 |

## 代码理解脉络

### 全景图

```
┌──────────────────────────────────────────────────────────────────┐
│                    第 3 层 · Supervisor 编排                      │
│                   supervisor_agent.py                             │
│                                                                  │
│  route → setup_auth → dispatch_review + dispatch_production      │
│                           → aggregate → audit_report              │
│                                                                  │
│  核心机制：                                                       │
│  · AgentRouter — 意图分类→目标列表                               │
│  · STS — Token Exchange 鉴权链路                                 │
│  · AuditLogger — 全链路审计追踪                                  │
├──────────────────────────────────────────────────────────────────┤
│                    第 2 层 · 子 Agent                             │
│            agents/review_agent.py   agents/production_agent.py    │
│                                                                  │
│  审核 Agent：                    生产 Agent：                    │
│  · review_order(oid)             · assess_material()             │
│  · 客户信用评估                    · assess_machine_load()         │
│  · 异常检测                       · assess_feasibility()          │
│  · 风险评级（高/中/低）              · 交期可行性判断               │
├──────────────────────────────────────────────────────────────────┤
│                    第 1 层 · 鉴权 + 审计                          │
│            auth/token_exchange.py   auth/audit_logger.py          │
│                                                                  │
│  鉴权：                          审计：                           │
│  · Token Exchange (RFC 8693)      · Trace ID 串联               │
│  · RBAC 权限矩阵（5角色）            · 结构化日志（JSON）           │
│  · 最小权限 + 短时效               · 不可否认性                   │
└──────────────────────────────────────────────────────────────────┘
```

### 阅读顺序（自底向上）

```
第 1 步（10min）→ auth/token_exchange.py
   理解 Token Exchange 和 RBAC 权限模型
   关键问题：子 Token 的权限为什么不能超过父 Token？

第 2 步（10min）→ auth/audit_logger.py
   理解审计日志的结构和 Trace ID 串联
   关键问题：审计日志的不可否认性如何保证？

第 3 步（15min）→ agents/agent_router.py
   理解意图识别的路由策略
   关键问题：关键词路由的优缺点？什么场景下该升级为 LLM 路由？

第 4 步（15min）→ agents/review_agent.py + agents/production_agent.py
   对比两个子 Agent 的职责边界
   关键问题：为什么审核 Agent 和生产 Agent 要分开？不放在同一个 Agent 里？

第 5 步（30min）→ supervisor_agent.py（重点）
   按流程读：route → setup_auth → dispatch → aggregate
   关键问题：Supervisor 怎么知道该调度哪个子 Agent？
```

### 三个"为什么"

| 设计决策 | 为什么这样？ |
|---------|-------------|
| 为什么拆成三个 Agent（Supervisor + 审核 + 生产）而不是一个？ | 职责分离：每个 Agent Prompt 更专注（审核只做风控，生产只看产能），扩展性更好（新增"财务 Agent"无需改现有代码） |
| 为什么子 Agent 之间不直接通信？ | 避免耦合——所有协调走 Supervisor，子 Agent 只对自己的职责负责，不知道其他 Agent 的存在 |
| 为什么 Token 要设置短时效（5分钟）？ | 最小权限原则——子 Token 只在完成任务所需时间内有效，即使泄漏影响也有限 |

## 核心认知

1. **Supervisor 模式 = 拆解 + 分发 + 汇总** — 主 Agent 不做具体业务，只做调度；子 Agent 各司其职
2. **Token Exchange = 权限收缩链** — 用户 Token → 受限子 Token → 更受限的子 Token，每层缩小权限范围
3. **洋葱型防御 = 三层防护** — 网关层(JWT) → 运行时层(RBAC) → 工具层(二次验证)，层层过滤
4. **审计日志 = 不可否认性** — 谁在什么时间做了什么，记录不可修改
5. **多 Agent 的代价** — 需要额外的路由编排和结果聚合，不是所有场景都值得用

## 参考资料

### Day 1-2：多 Agent 协作

| 知识块 | 资料 |
|--------|------|
| ⑧ Agent 集群 | [LangGraph Multi-Agent 文档](https://langchain-ai.github.io/langgraph/concepts/multi_agent/) ⭐ · [《智能体设计模式》中文版 — Jimmy Song](https://jimmysong.io/zh/book/agentic-design-patterns/) ⭐ · [构建多 Agent 系统的 8 个最佳实践 — 知乎](https://zhuanlan.zhihu.com/p/1954596883117871493) |

### Day 3-4：鉴权体系

| 知识块 | 资料 |
|--------|------|
| ⑨ 鉴权体系 | [Okta Securing AI Agents](https://www.okta.com/sites/default/files/2025-12/Securing%20AI%20Agents.pdf) ⭐ · [Token Exchange RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693) · [企业级 Agent 信任模型 — 百度](https://developer.baidu.com/article/detail.html?id=7592455) ⭐