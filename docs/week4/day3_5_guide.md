# 第四周 Day3-5 — 鉴权体系 + 审计日志 + 联调

> **对应代码**：`auth/token_exchange.py` · `auth/audit_logger.py` · `supervisor_agent.py`
> **理论清单**：[`理论知识清单.md`](./理论知识清单.md) 第 4-9 节（Token Exchange / 洋葱型防御 / RBAC / 审计日志）

---

## 先看清全貌：Week 4 的两层新增

Week 4 在 Week 3 的基础上新增了两层：

```
Week 3 架构                     Week 4 架构
─────────────                   ─────────────
Agent 编排层                    Supervisor + 子 Agent
  (langgraph_agent.py)            (supervisor_agent.py + agents/)
        │                                │
        │                                ├── 鉴权层（新增）
        │                                │   auth/token_exchange.py
        │                                │   auth/audit_logger.py
        ↓                                ↓
MCP 工具层                        MCP 工具层（不变）
  (order_server.py)                (order_server.py)
  (resource_server.py)             (resource_server.py)
```

**鉴权层是 Week 4 的核心增量**——它插入在编排层和工具层之间，做三件事：

1. **Token Exchange**：把用户身份转换成子 Agent 的受限身份
2. **RBAC 校验**：检查身份是否有权调用目标工具
3. **审计日志**：记录谁在什么时候做了什么

---

## Day 3：鉴权体系

### 1. 为什么 Agent 系统需要鉴权？

Week 3 的 Agent 可以调用任何工具、看任何数据。这在 Demo 里没问题，但在生产环境里：

| 场景 | 风险 | 鉴权怎么做 |
|------|------|-----------|
| 用户只应该看自己的订单 | 用户 A 查到了用户 B 的订单 | Token 携带用户身份，工具执行前校验 |
| 子 Agent 不应该访问所有数据 | 审核 Agent 误改了订单状态 | 子 Agent 的 Token 只有只读权限 |
| 泄漏的 API Key 被滥用 | 恶意调用所有接口 | Token 短时效 + 最小权限 |

**一句话**：没有鉴权，Agent 就是一个"什么都能干"的超级管理员——出了事不知道谁干的，也拦不住。

### 2. Token Exchange（RFC 8693）

**核心概念**：

> 用户登录后持有一个"高权限 Token"。当 Agent 需要调用下游服务时，它拿着这个 Token 去换一个"低权限 Token"——权限只够完成当前任务。

```
用户 Token（管理员权限）
    │
    ▼
┌────────────────────────┐
│   STS                  │
│   (Security Token       │
│    Service)             │
│                        │
│   验证：父 Token 有效   │
│   检查：子权限 ≤ 父权限 │
│   签发：子 Token        │
│   （短时效·窄权限）     │
└────────────────────────┘
    │
    ├── 审核 Agent Token（只读·客户信息）
    ├── 生产 Agent Token（只读·库存设备）
    └── 兜底：权限不够则拒绝
```

**代码理解**（`token_exchange.py`）：

```python
class STS:
    def issue_user_token(self, user_id, role, ttl=3600):
        """签发用户 Token（1 小时有效）"""
        token = Token(subject=user_id, role=role,
                      permissions=ROLE_PERMISSIONS[role],
                      source="user", expires_at=time.time()+ttl)
        return token.token_id

    def exchange(self, parent_token_id, requested_role):
        """Token Exchange：权限收缩"""
        parent = self._issued_tokens.get(parent_token_id)
        # ① 检查父 Token 是否有效
        # ② 检查子角色权限是否 ≤ 父角色权限
        # ③ 签发子 Token（5 分钟有效）
        child = Token(..., source="token_exchange",
                      expires_at=time.time()+300)
        return child.token_id, "ok"
```

**三个关键设计**：

| 设计 | 为什么 |
|------|--------|
| **子 Token 权限 ≤ 父 Token 权限** | 防止权限升级——子 Agent 不能做父 Token 做不了的事 |
| **子 Token 5 分钟过期** | 最小权限——子 Agent 只在执行期间持有权限 |
| **source="token_exchange"** | 区分"用户签发的"和"Exchange 产生的"，审计时可追溯 |

### 3. RBAC 权限矩阵

**5 角色，每角色可调用不同的工具集合**：

| 角色 | 可访问工具 | 典型使用方 |
|------|-----------|-----------|
| `admin` | 全部（*） | 系统管理员 |
| `scheduler` | 订单查询 + 资源查询 + 排产建议 | Supervisor / 生产 Agent |
| `reviewer` | 订单详情 + 生产状态 + 客户查询 | 审核 Agent |
| `operator` | 订单列表 + 设备查询 + 库存（只读） | 车间操作员 |
| `viewer` | 仅订单基本信息 | 外部查看 |

**权限校验链**：

```python
class Token:
    def can_access(self, tool_name: str) -> bool:
        if self.is_expired():
            return False
        if "*" in self.permissions:
            return True
        return tool_name in self.permissions
```

### 4. 洋葱型防御模型

**三层防御，层层过滤**：

```
Layer 1: 网关层
  ── OAuth2 / OIDC JWT 验证
  ── 拒绝无效/过期 Token
  ── 代码中：STS.validate() 检查 Token 是否存在

Layer 2: 运行时层
  ── RBAC 权限校验
  ── 验证角色是否有权调用此工具
  ── 代码中：Token.can_access(tool_name) 检查权限

Layer 3: 工具层
  ── 执行前二次验证（可选）
  ── 审计日志记录
  ── 代码中：AuditLogger.log() 记录调用
```

> **类比**：网关层 = 门卫（检查有没有工牌），运行时层 = 部门门禁（检查能不能进这个部门），工具层 = 操作日志（记录你进了哪间房、做了什么）。

### 5. STS 紧急响应

生产环境 Agent 系统必须能快速响应安全事件：

```python
# 吊销单个 Token
sts.revoke(token_id)

# 一键吊销所有 Token（Agent Universal Logout）
sts.revoke_all()
```

**什么场景需要？**
- Token 泄漏（API Key 被窃取）
- Agent 行为异常（可能被注入攻击）
- 用户权限变更（降权/离职）

---

## Day 4：审计日志 + 联调

### 1. 为什么 Agent 系统需要审计日志？

Agent 系统是"黑箱中的黑箱"——用户问一个问题，Agent 可能调了 3 次工具、看了 5 个数据源。**没有审计日志，你永远不知道 Agent 做了什么**。

### 2. 审计日志记录什么？

```
Trace ID（全链路唯一）│ 主体（谁）│ 操作（做了什么）│ 目标（对谁）│ 参数 │ 结果
─────────────────────┼─────────┼───────────────┼───────────┼──────┼──────
a1b2c3d4e5f6        │ 用户    │ issue_token   │ STS       │ role  │ 成功
a1b2c3d4e5f6        │ STS     │ exchange      │ reviewer  │ ...   │ 成功
a1b2c3d4e5f6        │ 审核    │ dispatch      │ ORD001    │ ...   │ 完成
```

**代码理解**（`audit_logger.py`）：

```python
class AuditLogger:
    def __init__(self):
        self._trace_id = uuid.uuid4().hex[:12]  # 全链路唯一 ID

    def log(self, action, subject, target, params=None, result=""):
        entry = {
            "id": uuid.uuid4().hex[:8],
            "trace_id": self._trace_id,           # 所有日志用同一个 Trace ID
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "action": action,
            "subject": subject,
            "target": target,
            "params": params or {},
            "result_summary": result[:200],
        }
        self._entries.append(entry)
```

**Trace ID 串联全链路**：

```
用户请求 ── Trace: a1b2c3d4
    │
    ├── STS.issue_user_token()   ── log: trace=a1b2c3d4
    ├── STS.exchange(reviewer)    ── log: trace=a1b2c3d4
    ├── dispatch_review(ORD001)   ── log: trace=a1b2c3d4
    ├── get_order_detail(ORD001)  ── log: trace=a1b2c3d4
    └── review_order complete     ── log: trace=a1b2c3d4
```

**审计报告样例**：

```
🔍 审计报告 (Trace: a1b2c3d4e5f6)
  调用次数：6
  时间范围：2026-07-27T10:30:00 ~ 2026-07-27T10:30:15

  [INFO] issue_token → STS @ 10:30:00
  [INFO] exchange_token → review @ 10:30:01
  [INFO] exchange_token → production @ 10:30:01
  [INFO] dispatch → review_agent @ 10:30:02
  [INFO] sub_call → ORD001 @ 10:30:03
  [INFO] sub_call → feasibility @ 10:30:05
```

### 3. 完整联调流程

```
用户：今天先做哪些订单？

① 路由
   AgentRouter.classify("今天先做哪些订单")
   → ["full"] → 需要调度所有子 Agent

② 鉴权
   STS.issue_user_token("user_001", "scheduler")
   STS.exchange(user_token, "reviewer")  → 审核 Token
   STS.exchange(user_token, "scheduler") → 生产 Token

③ 分发审核 Agent
   dispatch_review(["ORD001", "ORD003", "ORD005"])
   → 每个订单：查详情 → 查客户信用 → 判风险等级

④ 分发生产 Agent
   dispatch_production(["ORD001", "ORD003", "ORD005"])
   → 查材料库存 → 查设备负载 → 估交期可行性

⑤ 汇总
   综合 3 个订单的风险评级 + 产能评估
   → 输出：优先级排序 + 原因

⑥ 审计报告
   打印全链路 Trace 记录
```

---

## 学习路径

```
上午 · 理论消化
  ├─ Day 3：Token Exchange + RBAC + 洋葱型防御
  │  代码对照：auth/token_exchange.py
  └─ Day 4：审计日志 + 联调
     代码对照：auth/audit_logger.py + supervisor_agent.py

下午 · 编码 + 联调
  ├─ 跑 python supervisor_agent.py --demo
  ├─ 看审计日志输出，理解全链路追踪
  └─ 理解 Supervisor 的四步编排流程
```

---

## 核心认知（Day3-5 最重要的 5 句话）

1. **Token Exchange = 权限收缩** — 父 Token 换子 Token，每换一次权限缩小一点。子 Agent 永远不能做父 Token 做不了的事
2. **子 Token 短时效** — 5 分钟过期，泄漏了影响有限。这是最小权限原则的具体体现
3. **洋葱型防御 = 三层不要只做一层** — 网关层拦无效 Token，运行时层拦越权调用，工具层留审计记录
4. **Trace ID 串联一切** — 一个用户请求对应一个 Trace ID，所有日志都带着它。出问题时按 Trace ID 查，就能还原完整调用链
5. **审计日志不可否认** — 日志记录的行为本身不可修改。谁做了什么、什么时候做的，都有据可查

---

## 参考资料

| 知识块 | 资料 |
|--------|------|
| ⑨ 鉴权体系 | [Okta Securing AI Agents 白皮书](https://www.okta.com/sites/default/files/2025-12/Securing%20AI%20Agents.pdf) ⭐ · [Token Exchange RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693) · [企业级 Agent 信任模型 — 百度](https://developer.baidu.com/article/detail.html?id=7592455) ⭐ · [阿里云 Agent 权限管理](https://help.aliyun.com/zh/idaas/eiam/user-guide/agent-permission-management) |