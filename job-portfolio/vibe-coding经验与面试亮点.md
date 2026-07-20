# Vibe Coding 项目经验与面试素材

> 基于三个真实项目提炼：token-hub（Go 全栈 LLM 网关）、token-docs（规格驱动文档仓库）、retrosys（A股复盘系统，进行中）
> 整理日期：2026-07-07

---

## 一、三个项目总览

| 项目 | 定位 | 技术栈 | 我的角色 | 状态 |
|------|------|--------|---------|------|
| **token-hub** | 多租户 LLM API Key 代理网关 | Go 1.19 + Gin + GORM + Vue 3 + Element Plus | 全栈 + 架构 | 生产可运行，前端重构中 |
| **token-docs** | token-hub 的文档仓库 | 规格驱动文档体系（12 阶段编号）| 文档工程 + 需求分析 | 持续维护，17 分支合并 |
| **retrosys** | A股盘后复盘系统 | Vue 3 + Vite + FastAPI + vue-pure-admin | 全栈 + 需求工程 | Phase 1 编码准备阶段 |

三者的递进关系：token-hub（生产级全栈落地）→ token-docs（把全栈经验抽象成文档工程方法论）→ retrosys（用方法论驱动新项目，且进行中、暴露真实挑战）。

---

## 二、Vibe Coding 项目经验（跨项目提炼）

### 1. 规格驱动的 AI 协作开发

三个项目共同的方法论：**规格→计划→任务三件套，强约束流转**。

- **token-hub**：每个 spec 目录含 `spec.md` / `tasks.md` / `checklist.md`，规格用 SHALL/WHEN/THEN 风格写需求；commit 必须同包代码 + spec + plan（`CLAUDE.md:78-113`）
- **token-docs**：`README.md:38-43` 强制"规格→计划→任务"流转 + "实现后核对源头"规则——原文承认"之前多次出现只做了一部分、剩下的丢了的情况"
- **retrosys**：需求三层文档（`requirement.md` 业务语言 → `REQ-xxx.md` 技术语言 → `PROD-xxx.md` 设计语言）+ 编码准入条件（REQ 已评审 + PROD 存在，`README.md:344`）

**可迁移经验**：AI 编码最大的风险不是写错代码，而是"做了一部分丢剩下的"。用规格文档约束 AI 的执行边界，用 checklist 强制核对，能显著降低遗漏。规格用 SHALL/WHEN/THEN 而非自然语言，是为了让 AI 能机械执行验收。

### 2. 多 AI 工具分工协同

不是单工具包打天下，而是按能力分工：

| 工具 | 角色 | 落地位置 |
|------|------|---------|
| Claude | 深度分析、架构设计、复杂算法、技术文档 | CLAUDE.md 作为协作中枢 |
| Trae | 编码执行、按规则落地 | `.trae/rules/` 按领域加载 |
| CodeGraph | 提架构方案前验证影响范围 | token-hub 强制 `codegraph explore` |
| Understand-Anything | 扫描代码生成知识图谱、自动产出 ONBOARDING | `.understand-anything/` 索引 |
| Lingma / CodeBuddy | 代码补全、跨文件审查 | — |

**可迁移经验**：每个 AI 工具配专属规则文件，按需加载，避免上下文污染。CLAUDE.md 定红线，.trae/rules 定领域规范，AI-CONTEXT.md 定当前状态——三者分工不重叠。

### 3. AI 协作的工程化防线

token-hub 的**四防线验收**值得专门讲（`CLAUDE.md:39-49`）：

1. 计划验证（spec/plan 完整性）
2. CodeGraph 验收（影响范围核对）
3. CR 批判式走读（逐行质疑，不通过禁止提交）
4. 部署前审批

retrosys 的补充防线：CI 4 job（web/frontadmin/backend/security）+ 真实 DB + 覆盖率 80% 门禁 + Git Hooks 敏感信息检测 + pre-push 测试套件。

**可迁移经验**：AI 产出的代码必须有自动化防线兜底，不能靠人眼。四防线中任意一环松懈，质量就会漏到生产。

### 4. 文档作为 AI 的上下文接口

token-hub 的四层文档体系：

| 层级 | 文件 | 作用 |
|------|------|------|
| 红线层 | `CLAUDE.md` | 协作红线 + 8 角色专家评估体系（产品/架构/测试等） |
| 规范层 | `.trae/rules/` 8 份 | 按领域按需加载（架构/数据库/API 集成/运维） |
| 状态层 | `AI-CONTEXT.md` + `CONTEXT.md` | 项目当前状态、缺功能、企业需求 |
| 流程层 | `DEVELOPMENT.md` | 7 阶段开发流程（原型→后端→对接→单测→集成→E2E） |

**可迁移经验**：把"项目当前状态"写成显式文档（AI-CONTEXT.md），让任何 AI 工具接手时秒懂进度，不用重新探索。这是降低 AI 协作上下文成本的关键。

### 5. 需求工程化防止 AI 漫游

retrosys 的实践：

- 8 个需求（REQ-001~008）各有评审状态表
- 编码准入条件：REQ 已评审 + PROD 存在
- 目前仅 REQ-001 准入编码——流程会主动阻断未评审需求进入编码
- 术语表 60+ 条（分 7 类），消除歧义
- 需求关联图显式标注上下游依赖

**可迁移经验**：AI 不会替你做需求决策。需求工程化是把"人的判断"前置，让 AI 在已决策的边界内执行。准入机制看似拖慢进度，实则防止了"AI 帮你把错误的需求实现得很漂亮"。

### 6. 计划文档"面向 AI 代理"写

token-docs 的 `04-plans/2026-06-03-billing-implementation-plan.md` 开头直写"面向 AI 代理的工作者"：Phase 0-11 拆解 + TDD（先写测试再写实现）+ 决策编号引用（#14/#25/#26）。

**可迁移经验**：写给 AI 看的计划文档要包含：阶段拆解、决策引用号、测试先行、验收标准。这样 AI 能凭文档独立完成任务，不需要人反复介入澄清。

---

## 三、面试亮点

### token-hub

1. **密钥池加权随机 + 故障熔断自愈**（`internal/core/key_pool.go`）
   - `Pick()` 累加权重匹配；`ReportFailure` 连续失败达阈值自动禁用；`TryRecover` 超过 retryInterval 后标记候选恢复
   - RWMutex 保护并发；`maskKey` 脱敏
   - 测试：`key_pool_test.go:9-32` 60000 次采样验证 1:2:3 分布，容差 ±0.01

2. **SSE 流式透传双协议适配**（`internal/proxy/stream.go`）
   - 协议无关 `streamSSEResponse` + transform 回调，OpenAI/Claude 双协议适配
   - `ReplaceModelField` 用 `json.RawMessage` 部分反序列化，避免丢未知字段（`stream.go:513-540`）
   - 逐 chunk 入站/出站日志 + 首末 chunk 时间统计

3. **依赖注入 + 优雅关闭**（`cmd/main.go:36-388`）
   - 全程手工 DI（Repo→Service→Handler），按"配置→日志→DB→密钥池→cron→HTTP"顺序启动
   - SIGINT/SIGTERM 后 `srv.Shutdown(ctx)` 30s 超时，关 DB→同步日志

4. **TraceID 链路追踪**（`internal/monitor/trace_store.go`）
   - 环形缓冲区 + 自定义 Zap Core，含 trace_id 的日志同时落文件和内存
   - 按前缀检索供 `/dashboard/traces` 查询

5. **独创四防线验收 + 8 角色专家评估**（`CLAUDE.md:39-49,182-354`）
   - 计划验证 → CodeGraph 验收 → CR 批判走读 → 部署前审批
   - 8 角色专家（/1 产品、/3 架构、/5 测试…）独立审视

### token-docs

1. **计费规格典范**（`02-specs/G04a-billing-spec.md`）
   - 一份规格 49 条编号决策 + 5 模块 + 3 流程图
   - 与中转模块边界契约：`PreConsume(snapshot, est)` / `Settle(requestId, usage)`
   - 决策可追溯到代码每一处

2. **双轨追溯体系**
   - `00-taskregister/taskregister-index.md`：跨会话任务追踪，完成后只标记不删除，附"规格需求盘点"（24 份活跃规格 × 26 项未完成需求按 P0-P3 分级）
   - `03-design/kernel-doc/proxy-billing-kernel.md`：核心逻辑抽象成伪代码 + 数据流图 + 退款流程汇总图

3. **对标分析能力**（`09-reports/`）
   - 对标 lexy-admin + lexy-web 两个项目，能力对比矩阵 + 缺口清单 + 实施顺序
   - 50+ 份报告含四角色/8 角色/9 角色多视角评审、生产安全审计、需求实现遗漏评估

### retrosys

1. **需求→规范→编码准入机制**（`README.md:332-365`）
   - 8 项需求评审状态表追踪，编码准入条件显式定义
   - 未评审需求被流程阻断进入编码——少见的需求工程化实践
   - 任务驱动 5 阶段工作流（澄清→拆分→确认→执行→验收），阶段 0 未通过禁止进入阶段 1

2. **多端架构 + 双通道认证**（`README.md:60-65`、`backend/app/core/config.py:33-39`）
   - Web（5173）+ FrontAdmin（5174）+ Backend（8000）+ 需求挖掘 CLI 四入口
   - 双 Axios 实例 + 双通道认证（webBearer 7天5设备 / adminBearer 8h1设备）

3. **CI 含真实 DB 的安全 job**（`.github/workflows/ci.yml`）
   - backend-validate 用真实 MySQL 8.0 + PostgreSQL 16 而非 SQLite mock
   - wait-for-db 脚本 + 覆盖率 80% 门禁（Python 解析 coverage.xml 强制）+ pip-audit/pnpm audit

4. **需求挖掘 CLI 工具**（`retrosys_cli/elicit.py`）
   - 5 阶段挖掘：vision → scenario → deep-dive → prioritize → validate
   - 交互式 + 批量双模式，会话保存/恢复，--dry-run 试运行

5. **进度可视化三视图**
   - 百分比进度条 + 评审状态表 + Phase 开发顺序，含 14 项子任务依赖关系

---

## 四、缺点与教训

### token-hub

1. **G04a 计费综合评分 67/100**（`docs/reports/G04a-billing-completeness-evaluation-2026-06-02.md`）
   - 异常容错 45 分、可观测性 40 分、多模态计费 10 分
   - 3 个 P0：并发竞态、企业池原子性、Redis 故障降级缺失
   - 8 个 P1：锁过期重复扣费、PriceSnapshot 结构、错误码体系等
   - **教训**：计费这种高一致性场景，AI 协助实现后必须做并发场景的专项审计，不能只看单线程 happy path

2. **Go 1.19 锁版本**（`README.md:7` + `go.mod:3`）
   - 生产服务器不支持更高版本，限制新语法/依赖
   - **教训**：基础设施锁定会传导到开发体验，应在架构早期评估升级路径，或隔离关键服务的运行环境

3. **应用层维护引用完整性，不用外键**（`sql/001_init.sql` + `rules_database.md` 禁止项）
   - 迁移灵活但失去 DB 层一致性保护
   - **教训**：这是权衡决策，面试时讲清"为什么这么选 + 代价是什么"即可，不必回避

4. **front/ 原型暂停**（`README.md:9`、`AI-CONTEXT.md:5-13`）
   - vue-pure-admin + Mock 搭完 6 个 Mock 文件后停摆
   - 缺失 Provider-Model 关联页、Dashboard 图表、密钥健康指示器
   - **教训**：原型先行验证思路是好的，但要明确"暂停"还是"废弃"，避免代码库残留半成品

5. **历史踩坑（可面试当故事讲）**
   - **api-client 跳过 api-spec 对照** → 10+ 页面接口路径和字段名全不一致，登录成功无法跳转、列表全空（`rules_api_integration.md:325-328`）
   - **`generateTempPassword()` 用循环索引而非 `crypto/rand`** → 所有临时密码固定为 `abcdefghij`
   - **教训**：这两次踩坑后建立了"API 契约强制对齐"规则（8 项核对 + httptest）和"安全编码规范"。踩坑→建规是工程成熟的表现

### token-docs

1. **文档与代码不同步**（`09-reports/g13-implementation-traceability-20260624.md`）
   - G13/G13.2 完成度仅 **9%**——权限矩阵 18 项里 17 项未实现，`web-portal/` 目录根本不存在
   - F11 自报完成率 60%（23 完成 + 12 半完成 + 11 未实现）
   - **教训**：文档体系再完善，没有"实现后核对源头"的强制执行就会脱节。规则写了"必须核对"，但没有自动化的核对机制

2. **维护成本巨大**
   - `09-reports/` 单目录 50+ 份报告
   - `api-spec.md` 留下 4 个 archived 版本（20260604/0611/0613/0622）
   - `02-specs/` 含 10+ 个 `_archived-*` 文件
   - **教训**：文档量超过代码量时，要警惕文档自身的维护负债。归档机制要有，但也要定期清理

3. **真实 BUG 暴露的体系盲区**
   - **计费差异 BUG：平台亏损 97.7%**（`09-reports/billing-cache-double-charge-20260619.md`）——世纪互联 Claude 协议不返回缓存 token + `calculator.go:49` 缓存双重计费 + ratio 配置错误三连
   - **G12a spec 漏 7 项关键变更点**（`09-reports/G12a-audit-gap-analysis-20260615.md`）——通过 grep + CodeGraph 发现 24 项变更而非原 17 项
   - **2 项 P0 遗漏**（`09-reports/token-hub-需求实现遗漏评估报告-2026-05-26.md`）：`key_pool.go` 未接 `RecordKeyHealth`、首次启动无种子数据初始化导致裸部署代理完全不可用
   - **教训**：文档体系无法防止低级运维 bug 和协议适配 bug，必须靠测试覆盖 + CodeGraph 静态校验兜底

### retrosys

1. **进度严重不均**（`README.md:22-31`）
   - 需求体系 100%、规范体系 100%，但数据库 0%、数据采集 0%、后端骨架仅 30%
   - **教训**：过度规划 vs 编码滞后是 vibe coding 的典型陷阱——用"规划感"代替了"交付感"。规范做满了反而是一种拖延

2. **5 个架构开放问题待决**（`docs/ARCHITECTURE_OVERVIEW.md:251-258`）
   - K 线展示库选型（ECharts vs TradingVue vs Lightweight Charts）
   - 定时任务采集粒度、成本导入 Excel 模板字段、板块/概念主数据源、MVP 是否引入 Redis
   - **教训**：开放问题不解决，编码准入就卡住。这是流程的"正确"副作用，但要控制决策节奏，避免一个选型卡住整条链路

3. **过度工程化风险**
   - 规范体系 10 份文档（最大 95KB/2182 行）+ 四角色评估 35KB，但代码仅 30%
   - 自评"规范写了但缺少强制执行机制和验证手段"（`review-spec-four-perspective-20260523.md:775`）
   - **教训**：规范的价值在于执行。没有自动化校验的规范只是文档，反而给人"已经很完善"的错觉

4. **四角色评估发现的 6 项交叉问题**（`review-spec-four-perspective-20260523.md:716-724`）
   - 跨数据库一致性策略缺失（X1）
   - 金融精度测试缺失（X2，规则定义了 Numeric 但无测试）
   - 实时行情推送架构缺失（X3）
   - 测试数据工厂缺失（X4）
   - `database-guide.md` 与 coding-conventions 矛盾（X5，示例用 Float 违反 Numeric 硬性规则）
   - 前后端共享代码缺失（X6）
   - **教训**：多角色评审能发现单视角漏掉的问题，但评审发现的问题必须进任务追踪，否则等于没发现

5. **后端骨架大量 [待创建]**（`README.md:138-152`）
   - security.py / exceptions.py / state_machine.py / request_tracing.py / api/v1/ / services/ / repositories/ / models/ / schemas/ 全部待创建
   - **教训**：进行中项目要诚实标注"待创建"，这比假装完成更专业。面试时讲"哪些做了、哪些没做、为什么"比"全做了"可信得多

---

## 五、面试讲述策略

1. **讲方法论，不讲工具**：vibe coding 不是"让 AI 写代码"，而是"用工程化方法约束 AI 协作"——规格驱动、多工具分工、四防线验收、需求准入。工具会换，方法论不会。

2. **讲数据，不讲形容词**：60000 次采样 ±0.01、G04a 67/100、G13 完成度 9%、计费亏损 97.7%、49 条决策的规格——数字让故事可信。

3. **讲教训，不讲顺利**：api-client 跳过 spec 对照 → 接口全乱；临时密码固定 `abcdefghij` → 建安全规范。踩坑 + 改进比"一直顺利"更有说服力，也更能证明你真的做过。

4. **讲权衡，不讲对错**：不用外键、Go 1.19 锁版本、规范 100% 但代码 30%——每个决策讲清"为什么选 + 代价是什么"，体现架构判断力。

5. **三个项目讲递进**：
   - token-hub = 我能写生产级全栈
   - token-docs = 我能把经验抽象成可复用的文档工程方法论
   - retrosys = 我能用方法论驱动新项目，且能诚实面对进行中项目的真实挑战

   这条线展现的是从"写代码"到"建体系"到"做决策"的成长轨迹。

---

## 附：关键证据文件索引

### token-hub
- `E:/workspace/js_workspace/projects/token-hub/CLAUDE.md` — 协作红线 + 8 角色评估 + 四防线
- `E:/workspace/js_workspace/projects/token-hub/.trae/rules/rules_api_integration.md` — API 契约对齐规则 + 历史踩坑
- `E:/workspace/js_workspace/projects/token-hub/cmd/main.go` — DI + 优雅关闭
- `E:/workspace/js_workspace/projects/token-hub/internal/core/key_pool.go` + `key_pool_test.go` — 密钥池加权 + 熔断
- `E:/workspace/js_workspace/projects/token-hub/internal/proxy/stream.go` — SSE 双协议
- `E:/workspace/js_workspace/projects/token-hub/internal/monitor/trace_store.go` — TraceID 链路追踪

### token-docs
- `E:/workspace/js_workspace/projects/token-docs/README.md` — 文档体系总览与流转规则
- `E:/workspace/js_workspace/projects/token-docs/02-specs/G04a-billing-spec.md` — 计费规格典范（49 条决策）
- `E:/workspace/js_workspace/projects/token-docs/04-plans/2026-06-03-billing-implementation-plan.md` — 面向 AI 代理的计划范本
- `E:/workspace/js_workspace/projects/token-docs/03-design/kernel-doc/proxy-billing-kernel.md` — 内核逻辑伪代码
- `E:/workspace/js_workspace/projects/token-docs/00-taskregister/taskregister-index.md` — 跨会话任务索引
- `E:/workspace/js_workspace/projects/token-docs/09-reports/g13-implementation-traceability-20260624.md` — 完成度 9% 回核
- `E:/workspace/js_workspace/projects/token-docs/09-reports/billing-cache-double-charge-20260619.md` — 计费 BUG 根因

### retrosys
- `E:/workspace/js_workspace/projects/retrosys/README.md` — 进度 + 准入 + Trae 指南
- `E:/workspace/js_workspace/projects/retrosys/docs/ARCHITECTURE_OVERVIEW.md` — 5 个开放问题（第 251-258 行）
- `E:/workspace/js_workspace/projects/retrosys/docs/system-analysis/review-spec-four-perspective-20260523.md` — 四角色评估
- `E:/workspace/js_workspace/projects/retrosys/docs/specs/reqs/index.md` — 需求索引与关联图
- `E:/workspace/js_workspace/projects/retrosys/retrosys_cli/elicit.py` — 需求挖掘 CLI
- `E:/workspace/js_workspace/projects/retrosys/.github/workflows/ci.yml` — CI 4 job + 真实 DB
