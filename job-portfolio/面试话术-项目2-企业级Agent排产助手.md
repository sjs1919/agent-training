# 项目经历 2：企业级 Agent 排产助手（demo）

> 类型：技术类（AI 工程化）
> 来源：Agent-Training 四周实战 + week5 工程化整合（2026-07-03 ~ 08-07）
> 框架：业务架构 → 业务流程 → 技术架构 → 设计模式 → 技术亮点 → 难点
> 状态：初稿（2026-08-08）+ 六角色审阅建议（见第十节）

---

## 一、业务架构

**行业**：制造业智能调度（3D 打印 / CNC 排程排产），承接项目1智能机器管理系统的下一环

**业务定位**：面向制造业排程排产的对话式助手。用户用自然语言问生产问题，Agent 自动调用工具查数据、检索合同、综合分析后回答——把「业务人员看报表、翻合同」变成「直接问系统」。

**业务规模**：
- 数据域：订单 / 库存 / 设备 / 客户 4 类业务数据 + 3 份合同知识库（特殊条款）+ 历史延期记录
- 覆盖场景：订单排期、订单详情、紧急与瓶颈、客户评估、库存影响、合同条款（RAG）6 类
- 运行模式：单 Agent（快答） / 多 Agent Supervisor（分派专业子 Agent 协同）

**业务边界**：
- 上游：MES 排程排产业务数据（订单/库存/设备/客户 CSV 模拟）
- 本系统：Agent 编排（LangGraph 状态机）+ 工具调用（订单/资源查询）+ RAG 检索（合同条款）+ 权限治理（STS/RBAC/审计）
- 下游：LLM 主备 provider（火山豆包主 + DeepSeek 备）

**核心业务价值**：
1. 从「看报表 + 翻合同」到「自然语言问答」，降低业务人员使用门槛
2. 合同特殊条款（广州航天、赔付规则等）精确命中，RAG 比纯向量检索准
3. 以制造业真实约束为载体验证 Agent 调度场景可行性（团队级验证，非规模化）

---

## 二、业务流程

### 2.1 单 Agent 流程（LangGraph 状态机）

```
用户提问 → analyze_intent（意图识别）
        → select_and_execute（LLM 决策调哪些工具 → 执行 → 注入 tool 结果）
        → evaluate_results（评估结果是否足够，检查质量+数据完整性）
        → should_continue 条件边：末条是 tool 结果 → 继续循环；是 assistant 文本 → generate_answer
        → generate_answer（经 guardrails 输出护栏校验）→ END
安全阀：迭代 ≥5 轮强制结束（防死循环）
```

### 2.2 多 Agent 流程（Supervisor 调度）

```
用户提问 → 意图路由（router 关键词：review/production/full/query）
        → STS 签发用户 Token → 交换子 Agent 受限 Token（reviewer/scheduler，5min TTL）
        → 分派 review_agent（订单评审：订单详情/生产状态/客户 权限）
        → 分派 production_agent（生产评估：全工具权限）
        → 子 Agent 工具调用经 registry 走 RBAC（无权拒绝 + 审计）
        → LLM 汇总综合回答
```

### 2.3 RAG 混合检索流程

```
向量召回（Chroma/MiniLM） + BM25（jieba 分词）
        → RRF 融合（Reciprocal Rank Fusion，两路排名 1/(k+rank) 累加）
        → Cross-Encoder 重排（BAAI/bge-reranker-base，精排 top3）
        → 命中合同原文返回
为什么混合：纯向量中文召回弱（top1 常召回错误文档），BM25 补关键词字面命中（"广州航天"必须命中）
```

### 2.4 LLM 调用流程（成本控制）

```
语义缓存（L2，近义问题命中跳过整图执行，~50ms）→ 未命中
  → L1 精确缓存（相同 prompt 命中 <1ms，0 token）→ 未命中
  → call_llm（遍历 PROVIDERS，主备顺序第一个成功即返回，失败自动降级）
```

---

## 三、技术架构

### 3.1 分层架构（Harness 三层）

```
入口层     main.py（CLI）· api.py（FastAPI 网关 /ask /health /threads/{id}/history）
配置层     config.py（单一 PROVIDERS 注册表，主备 fallback 单一事实源）
基座层     core/llm_client.py（统一 call_llm + 主备降级 + 连接池 + L1 精确缓存）
缓存层     cache/llm_cache.py（L1 精确缓存 SQLite）· semantic_cache.py（L2 语义缓存 Chroma）
工具层     tools/registry.py（ToolRegistry O(1) 查找 + 参数白名单 + RBAC 强制 + tracer 接入）
           order_tools / resource_tools / data（CSV）· mcp_servers.py（FastMCP 展示）
RAG 层     rag/retriever.py（BM25+向量+RRF+Cross-Encoder 混合检索）· knowledge_base.py
编排层     graph/single_agent_graph.py（LangGraph 状态图 + SqliteSaver checkpointer）
           graph/context_compressor.py（summarization buffer 上下文压缩）
Agent 层   agents/single_agent.py · router.py · review_agent.py · production_agent.py · supervisor.py
权限层     auth/token_exchange.py（STS，RFC 8693）· guard.py（RBAC）· audit_logger.py
安全层     guardrails/（越权指令/敏感信息检测 + 缺失段落检查 + block/warn/off）
评估层     eval/（10 组 ground truth + 3 维指标 + runner + 回归基线）
观测层     observability/tracer.py（Span，OTel 同构）· exporter.py（console/otel/OTLP）
```

**Harness 三层对应**：
- 编排层 = `graph/` + `agents/`（LangGraph 状态机驱动 Agent 循环）
- 权限层 = `auth/`（STS 令牌交换 + RBAC 守卫 + 审计，洋葱型三道防线）
- 观测层 = `observability/`（Span 全链路追踪，OTel 同构接口）

### 3.2 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 语言 | Python 3.11+ | 全栈开发 |
| 编排 | LangGraph StateGraph | Agent 状态机编排 + SqliteSaver 持久化 |
| Agent | 单 Agent + Supervisor 多 Agent | 路由分派、受限令牌协作 |
| RAG | Chroma + BM25 + RRF + Cross-Encoder | 合同知识库混合检索 |
| 鉴权 | STS Token Exchange（RFC 8693）+ RBAC | 子 Agent 受限令牌 + 工具层强制权限 |
| 安全 | guardrails（block/warn/off） | 输出护栏、越权指令检测 |
| 观测 | 自研 Tracer（OTel 同构）+ 可插拔 backend | 全链路 span + token 用量 + Jaeger |
| 评估 | eval 模块（ground truth + 指标 + runner） | 回归基线 ≥7/10 |
| 工具 | ToolRegistry + 参数白名单 + 沙箱 + MCP | O(1) 查找、超时重试、进程隔离 |
| 部署 | FastAPI 网关 + Docker + compose | CLI → HTTP → 容器化 |

---

## 四、设计模式

### 4.1 状态图编排模式（LangGraph StateGraph）

核心循环「分析→选工具→执行→评估→生成」建模为状态图：
- **节点**：analyze_intent / select_and_execute / evaluate_results / generate_answer
- **条件边**：should_continue 判断「还要不要继续调工具」——末条是 tool 结果→循环，是 assistant 文本→出答案
- **安全阀**：迭代 ≥5 轮强制结束，防死循环
- **状态持久化**：SqliteSaver checkpointer，多轮对话 + 重启恢复（dict 消息保持，避免 add_messages 转对象风险）

### 4.2 注册中心模式（ToolRegistry）

对比 week1 的 if/elif 链，用字典 O(1) 查找替代：
- 参数白名单过滤（只传 Schema 定义字段，防 LLM 传多余字段）
- RBAC 强制（工具执行入口校验权限）
- tracer 自动埋点（每次工具调用自动记 span）

### 4.3 洋葱型安全纵深

三道防线逐层收口：
- 第 1 层：网关/运行时鉴权
- 第 2 层：STS 令牌交换（父令牌 → 受限子令牌，权限收缩校验防提权）
- 第 3 层：工具层 RBAC 强制（无权拒绝 + 审计 JSONL 落盘）

### 4.4 主备 fallback 模式

config.py 单一 PROVIDERS 列表（主备顺序）+ 统一 `call_llm(messages, tools)` 签名：
- provider 级 httpx 连接池（10 连接/provider，keep-alive 60s）
- 第一个成功即返回，失败自动降级
- 改主备只动一处列表，调用方不感知切 provider

---

## 五、技术亮点

### 5.1 单/多 Agent 双模式，一套代码

LangGraph 状态图（单 Agent）+ Supervisor 调度（多 Agent）双模式，按问题复杂度切换，共享工具层/RAG/鉴权

### 5.2 权限设计真实落地（非玩具）

- STS Token Exchange（RFC 8693）：父令牌 → 受限子令牌，5min TTL，权限收缩校验防提权
- RBAC 在工具层强制（洋葱第 3 层），无权拒绝 + 审计 trace_id 贯穿
- 多租户隔离（R8）：token + tenant_id 数据层过滤，FORCE_TENANT 强制模式

### 5.3 中文 RAG 四步混合检索

纯向量中文召回弱（top1 常召回错误文档）→ BM25(jieba) 补字面命中 + RRF 融合 + Cross-Encoder 重排，目标合同 top1、rerank 分 >0.9

### 5.4 两级缓存 + 成本熔断

- L1 精确缓存（SQLite，相同 prompt 命中 <1ms，0 token）
- L2 语义缓存（Chroma cosine，近义问题跳过整图 ~50ms，阈值 0.20 校准）
- CostTracker 自动计费 + 预算熔断

### 5.5 状态持久化 + 上下文压缩

- SqliteSaver checkpointer：`--chat --thread` 跨进程恢复会话
- summarization buffer：保留 system + 最近 N 条，中间用 LLM 摘要替代，控长对话 token 成本

### 5.6 可观测 OTel 同构

自研轻量 Tracer（Span/trace_id）+ 可插拔 backend（console/otel/OTLP 发 Jaeger），换 backend 不动业务代码

### 5.7 Agent 评估闭环（R6）

10 组排产场景 ground truth + 加权指标（工具调用准确率 F1 0.3 + 回答完整性 0.5 + 订单命中 0.2）+ runner 跑批，单 case 综合分 ≥0.6 通过，汇总 ≥7/10 过回归基线

### 5.8 交付闭环

CLI → FastAPI 网关 → Docker 容器化，生产化路径完整

---

## 六、难点

### 6.1 中文 RAG 召回质量差

纯向量（MiniLM）中文 top1 常召回「历史延期记录」而非目标合同，直接问答答错。

**解法**：四步混合检索（向量 + BM25 jieba 字面命中 + RRF 融合 + Cross-Encoder 重排），目标合同 top1、rerank 分 >0.9。

### 6.2 reranker 离线加载卡死

HF 未缓存时 HEAD 检查每个要等 Windows TCP 超时 ~21s × 5 retry，严重拖慢。

**解法**：直接 patch `huggingface_hub.constants`（import 时固化 HF_HUB_OFFLINE，运行时设 env 无效）；离线优先，未缓存才走代理下载。

### 6.3 多 Agent 越权风险

原 week4 无鉴权，子 Agent 可越权调工具（如评审 Agent 调生产全量工具）。

**解法**：STS Token Exchange（RFC 8693）父令牌→受限子令牌（5min TTL，权限收缩校验防提权）；RBAC 在工具层强制（洋葱第 3 层）；审计日志 trace_id 贯穿。

### 6.4 主备切换散落

week1/2/3 各维护一份 PROVIDERS，改 provider 要改多处。

**解法**：config.py 单一事实源 + 统一 `call_llm(messages, tools)` 签名 + provider 级 httpx 连接池。

### 6.5 LLM 成本失控

Agent 单轮可能 3-5 次 LLM 调用，token 消耗不可控。

**解法**：L1 精确缓存（<1ms 0 token）+ L2 语义缓存（Chroma cosine）+ 成本跟踪 + 预算熔断。

### 6.6 多轮上下文与重启恢复

进程重启后会话丢失，多轮对话无法续接。

**解法**：LangGraph SqliteSaver checkpointer（`--chat --thread` 跨进程恢复）；显式从 checkpoint 取历史，保持 dict 消息格式。

### 6.7 可观测 span 丢失

业务代码在 span 结束后才写 token 属性，立即导出会丢。

**解法**：延迟批量导出（整轮 query 结束才 flush），OTel 同构最小实现，换 backend 不动业务代码。

### 6.8 工具安全

LLM 可能传多余字段（如把 comment 字段带进 WHERE）、越权调工具。

**解法**：ToolRegistry 参数白名单过滤（只传 Schema 定义字段）+ RBAC 强制 + tracer 自动埋点。

### 6.9 Windows 控制台 GBK 乱码

状态 emoji 在 GBK 控制台显示乱码。

**解法**：包入口重配 stdout UTF-8（`demo/__init__.py`）。

### 6.10 容器化部署

模型缓存/运行时数据/网络镜像处理复杂。

**解法**：FastAPI 网关（/health /ask /threads/{id}/history）+ Dockerfile（清华源 torch CPU）+ compose（HF_ENDPOINT hf-mirror 加速、`DEMO_RUNTIME_DIR` 运行时卷分离、模型缓存挂载）。

---

## 七、面试话术（1 分钟版）

> 我独立实现了一个面向制造业排程排产的企业级 Agent 排产助手，核心是「LangGraph 状态图 + Supervisor 多 Agent + 权限治理」三层架构。用户用自然语言问生产问题，Agent 自动调工具查订单/库存/设备，检索合同条款，综合分析回答。
>
> 技术上覆盖 Agent 开发全链路：手写 ReAct 循环 → LangGraph 编排 → 多 Agent Supervisor 协作 → Token Exchange（RFC 8693）鉴权 → RAGAS 评估。RAG 端用 BM25 + 向量 RRF + Cross-Encoder 重排四步召回，解决中文 RAG 召回不准的问题。
>
> 多 Agent 用 Supervisor 路由到专业子 Agent（订单评审/生产评估），子 Agent 各持受限权限令牌，工具层强制 RBAC，审计 trace_id 贯穿，实现洋葱型三道防线。落地用制造业真实约束验证：合同赔付、航天件全检、PEEK 耗料公式规则引擎。

---

## 八、追问弹药

| 追问 | 回答要点 |
|------|----------|
| "为什么不用纯向量 RAG？" | 中文 MiniLM 召回弱，top1 常召回错误文档；BM25 补字面命中（"广州航天"必须命中）+ RRF 融合 + Cross-Encoder 精排 |
| "RRF 融合怎么算的？" | 两路排名 1/(k+rank) 累加（k=60），取融合后 topN 送重排 |
| "重排器用的什么？" | BAAI/bge-reranker-base，精排 top3，目标合同 rerank 分 >0.9 |
| "Token Exchange 怎么防提权的？" | 子令牌权限 ≤ 父令牌，交换时校验收缩，5min TTL |
| "RBAC 在哪一层强制？" | 工具层（洋葱第 3 层），每次工具调用经 guard.py 校验，无权拒绝 + 审计 |
| "上下文压缩怎么做的？" | summarization buffer：保留 system + 最近 6 条，中间用 LLM 摘要替代 |
| "评估怎么做的？" | 10 组 ground truth + 工具准确率/完整性/综合评分 3 维指标，回归基线 ≥7/10 |
| "两级缓存区别？" | L1 精确缓存 SQLite <1ms 0 token（相同 prompt）；L2 语义缓存 Chroma cosine ~50ms（近义改写） |
| "观测层怎么接 Jaeger？" | OTel 同构接口 + 可插拔 backend，OTEL_EXPORTER=otel 发 OTLP 到 Jaeger 4317 |
| "和项目1什么关系？" | 项目1是设备管理层（6 服务流水线），排产助手是决策层（Agent 排程排产），MES 排程演进路线里规划引入 Agent 智能调度 |
| "生产级差距在哪？" | 教学版验证：缺 JWT 签名/refresh token（权限）、采样/异步导出（观测）、增量索引/多租户 RAG、NL2SQL、CI 集成轨迹评估 |

---

## 九、口径红线（对面试官）

- 术语锚点可深可浅：VP/CTO 问「Agent 到什么深度」→ 讲 4-7 行全链路（ReAct→LangGraph→Supervisor→Token Exchange→RAGAS）；HR/猎头不问不主动展开
- **说「团队级验证」不说「规模化」**（demo 是验证可行性，非生产规模）
- 源码可追溯：`agent-training/demo/` + `agent-training/scripts/week1-4/`（repo 备索）
- 与简历叙事一致：AI 工程化 + 制造业落地 + 团队管理三重叠加

---

## 十、待办：六角色审阅建议（2026-08-08）

> 小明（AI 编程同事）+ 老张（Java 后端架构师）+ 老周（研发 VP）+ 李姐（HRBP）对项目2的深入审阅。

### 小明（AI 编程同事）— 最关注"真懂还是贴标签"

1. **RAGAS 表述失实风险**：文档「七、面试话术」1分钟版写「Token Exchange（RFC 8693）鉴权 → RAGAS 评估」，但 demo/eval 实际是**自研指标**（工具 F1 + 完整性 + 订单命中，加权 0.3/0.5/0.2），RAGAS 是 week4 的 `ragas_eval.py` 训练脚本，不在 demo 里。面试官若追问「demo 里 RAGAS 在哪」会穿帮。**建议**：话术改「→ 评估闭环」，把 RAGAS 放到「追问弹药」——「RAGAS 在 week4 训练脚本里跑过，demo 用自研指标更可控」。优先级：**高**
2. **话术「企业级」vs 口径「团队级验证」矛盾**：标题写「企业级 Agent 排产助手」，但口径红线说「团队级验证不说规模化」。面试官可能抓矛盾。**建议**：「企业级」指的是工程化方法论（权限/观测/评估/护栏这些生产级关注点），不是部署规模，话术里补一句「以工程化方法论验证可行性」消除歧义。优先级：中
3. **补一句"从手写原语到框架"的成长线**：你四周训练的主线是「手写 ReAct → LangGraph → Supervisor」，这是最能证明「真懂原理不是调 API」的证据。项目2文档在技术架构里没体现手写阶段，只有 LangGraph。**建议**：难点/亮点补一条「先手写循环理解原语，再换框架看清框架替你做了什么」。优先级：中
4. **补 guardrails 效果数据**：护栏能拦截什么、block 后怎么重试，缺具体例子。面试官问「护栏拦过什么真实内容」会答不上。**建议**：补一个越权指令/敏感信息的真实拦截样例。优先级：低

### 老张（Java 后端架构师）— 最关注"工程化够不够硬"

5. **补「生产级差距」的诚实度**：文档在追问弹药里列了差距（缺 JWT/refresh token、采样/异步导出、增量索引等），这很好，但可以更主动。老张会欣赏「知道 demo 和生产差距在哪」的诚实。**建议**：在话术或亮点里主动提一句「这是教学版验证，生产化路径我在 week5 差距表里已列」，反而加分。优先级：中
6. **补成本/规模数据**：老张关心「这个 demo 跑起来多大成本、多快」。目前缺「单轮 Agent 平均几次 LLM 调用、token 用量、缓存命中率、回答延迟」。**建议**：跑一轮记录真实数据（LLM 调用次数、token、耗时、缓存命中），补进追问弹药。优先级：中
7. **MCP 的定位要讲清**：文档亮点 5.1 和难点 6.8 提到 MCP，但 demo 默认走 local fast path，MCP 是展示（`MCP_MODE=mcp` 才走子进程）。面试官追问「MCP 到底用没用」会含糊。**建议**：明确「工具协议化的演进方向，本地 fast path + MCP 子进程两种模式」，不夸大。优先级：低

### 老周（研发 VP）— 最关注"这人能不能扛事"

8. **补「为什么做这个」的业务动机**：老周会问「公司为什么要做 Agent 排产助手？解决了什么真问题？」。当前文档业务架构偏技术，缺业务动机叙事（如「业务人员查报表、翻合同慢 → 用自然语言问答降门槛」）。**建议**：业务架构加一段「业务痛点 → 系统定位」的前置叙事。优先级：中
9. **补「未来演进」的路线**：老周想看「这人有没有把 Agent 落地到生产的规划」。项目1 MES 排程演进路线里已写「规划引入 Agent 智能调度」，项目2正好呼应。**建议**：补「从 demo 验证 → 生产落地的路径（接真实业务库 / 规则引擎 → Agent 调度）」承接项目1。优先级：中
10. **团队视角缺失**：这个项目目前是「个人实战」（用户自己做的），但老周招的是研发总监，关心「你能不能带团队做 Agent」。**建议**：话术补一句「已组织 2 场团队 AI 编程培训 + 规划团队 Agent 能力路线图」，把个人实战升级为团队能力建设。优先级：中

### 李姐（HRBP）— 最关注"一眼能懂 + 卖点鲜明"

11. **「企业级」标题对 HR 不友好**：李姐 15-20 秒扫简历，看到「企业级 Agent 排产助手」第一反应是「又是一个 demo 硬装生产」。**建议**：文档标题可保留「企业级」（面试用），但简历上改成「AI 排产助手（Agent 工程化验证）」更稳。优先级：低
12. **补「一个数字抓住眼球」**：项目1有「700+设备/4倍提速」，项目2缺一个能记住的数字。**建议**：沉淀一个真实数字（如「10 组排产场景回归基线 7/10」「6 类业务场景」「两级缓存省 90% token」需实测），放进 1 分钟话术开头。优先级：中

---

## 十一、三方不一致核对（面试话术 / demo 实现 / 知识学习）

> 2026-08-08 交叉核对：`面试话术-项目2`（本文档） vs `demo/` 实际代码 vs `docs/` 知识学习文档。
> 目的：找出面试陈述与代码事实、知识文档之间的矛盾，避免面试时被追问穿帮。

### A. 面试文档未同步 R1-R8（最严重）

**来源冲突**：`docs/week5/面试技术深度与应对策略.md`（2026-08-07 写）在「五、弱点应对策略」「四、各角色策略」中声称以下 4 项**未做**，但 R1-R8 已在同一天（08-07）全部修复并合入 demo：

| # | 面试文档声称「没做」 | demo 实际状态（R1-R8 已修复） |
|---|--------------------|-------------------------------|
| 1 | 弱点2：工具执行无沙箱/隔离，「工具和 Agent 同进程」 | **R1 已完成**：`tools/sandbox.py` 超时控制 + 指数退避重试（1s→2s→4s，最多 3 次） |
| 2 | 弱点3：无输出护栏，「最严重缺口」 | **R2 已完成**：`guardrails/` 模块，越权指令/敏感信息检测 + block/warn/off |
| 3 | Q1/弱点4：`evaluate_results` 是 noop | **R3 已完成**：`evaluate_results` 真校验（needs_retry / needs_more / ready_for_answer 标记） |
| 4 | 弱点4：上下文无限增长，「当前无」 | **R4 已完成**：`graph/context_compressor.py` summarization buffer 压缩 |

**风险**：面试若按旧文档应答「没做沙箱/护栏/压缩」，面试官实际看到代码有这些，会质疑「你不熟自己项目」。
**建议**：以 R1-R8 修复后的状态为准。对应弱点的回答改为「曾是无沙箱/无护栏，2026-08-07 已补 R1-R8，当前只剩 X/Y/Z gap」。

### B. 知识文档内部矛盾（复盘未更新）

**来源冲突**：`docs/week5/week5_收尾复盘.md` 缺口清单（08-07 修复前）列 R1-R8 为「未修」，但 `docs/week5/8大缺陷-可执行代码改造方案.md` + `demo/README.md` 验收清单显示 R1-R8 **全部已完成**。

| 复盘说 | 实际 |
|--------|------|
| 缺口#1：工具执行无重试 | R1 已修（sandbox.py） |
| 缺口#2：evaluate_results noop | R3 已修 |
| 缺口#3：无输出护栏 | R2 已修（guardrails/） |
| 缺口#4：无上下文压缩 | R4 已修（context_compressor.py） |
| 缺口#11：Docker 待验收 | 未变（Docker 环境仍未启动验收） |
| 缺口#12：Langfuse 未做 | 未变（自研 Tracer 替代） |

**建议**：更新 `week5_收尾复盘.md` 缺口清单为修复后状态，避免内部口径矛盾。

### C. RAGAS 表述（demo 用自研 eval，非 RAGAS）

**来源冲突**：面试话术 1 分钟版写「Token Exchange（RFC 8693）鉴权 → RAGAS 评估」，但：
- `demo/eval/` 用的是**自研指标**（工具 F1 + 完整性 + 订单命中，加权 0.3/0.5/0.2）
- RAGAS 是 `scripts/week4/ragas_eval.py`（week4 训练脚本），**不在 demo 里**

**风险**：面试官问「demo 里 RAGAS 在哪」会穿帮。
**建议**：话术改「→ 评估闭环」；RAGAS 放追问弹药——「RAGAS 在 week4 训练脚本跑过（4 指标），demo 用自研指标更可控」。week5 复盘也说「缺可运行评估脚本（如 RAGAS）」——实际上 R1-R8 的 R6 已补 eval/ 模块，复盘此条也已过时。

### D. 单 Agent 鉴权绕过（FORCE_AUTH 确为真 gap）

**来源冲突**：面试文档场景 4 说「单 Agent 模式 token=None 绕过鉴权，生产必须加 FORCE_AUTH 开关」。

**代码事实**：`demo/auth/guard.py:23` 确认「token=None 时放行（单 Agent 模式无鉴权）」。R8 只加了 **FORCE_TENANT**（多租户强制），**没有 FORCE_AUTH**。
- ✅ 面试文档此条**仍然成立**，是真 gap，可诚实承认
- 注意区分：R8 是 FORCE_TENANT，不是 FORCE_AUTH，别混淆

### E. MCP 定位（已实现但默认 local fast path）

**来源冲突**：面试文档弱点2 说「MCP 真进程隔离是『展示正确但未真隔离』」，但 R5 已实现 `tools/mcp_client.py`（stdio 子进程通信）。

**代码事实**：`demo/tools/registry.py:120` 默认 `MCP_MODE=local`（fast path），设 `MCP_MODE=mcp` 才走子进程。R5 是真实现但默认不启用。
**建议**：话术明确「工具协议化演进方向——本地 fast path + MCP 子进程双模式，生产默认走 MCP 子进程隔离」。

### F. 仍成立的真实 gap（可诚实承认）

交叉核对后确认以下 gap **未被 R1-R8 覆盖**，面试可诚实承认：

| gap | 位置 | 状态 |
|-----|------|------|
| 无单元测试 | 全局 | 已知，R1-R8 未覆盖 |
| 单 Agent 鉴权绕过 | `guard.py` token=None 放行 | 已知，缺 FORCE_AUTH |
| 检索质量阈值 | `rag/retriever.py` 无 rerank 分 < 阈值标记 | 未做 |
| 消息截断补充 | 上下文压缩已有（R4），但无硬截断 | 部分 |
| 按用户/租户计费 | `cost.py` 按会话计费 | 未做 |
| 熔断后自动恢复 | `cost.py` 无冷却时间 | 未做 |
| Docker 环境验收 | Docker Desktop 未启动 | 待验收 |
| Langfuse 看板 | 自研 Tracer 替代 | 未做 |
| 业务数据包/SLA 定义 | 全局 | 复盘缺口 #9/#10 未解决 |
| 增量索引/多租户 RAG | `rag/` | 未做 |
| 采样/异步导出 | `observability/` | 未做 |


