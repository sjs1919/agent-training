# demo 排产助手 — 业务架构 / 技术架构 / 技术难点 / 亮点

> 来源：`agent-training/demo/`（多 Agent 排产助手，week1-4 工程化整合版）
> 用途：一面 VP/CTO 版、二面下属版的技术弹药库；被追问"Agent 做到什么程度"时引用
> 整理日期：2026-08-05

---

## 一、业务架构

**定位**：面向制造业排程排产的对话式助手。用户用自然语言问生产问题，Agent 自动调用工具查数据、检索合同、综合分析后回答。

**数据域**（`demo/data/*.csv` + `contracts/*.txt`）：
- 订单（orders）、库存（inventory）、设备（machines）、客户（customers）
- 合同知识库：3 份合同特殊条款 + 历史延期记录（RAG 数据源）

**能回答的问题类型**（6 类业务场景）：
| 场景 | 示例问题 | 涉及工具/能力 |
|------|---------|--------------|
| 订单排期 | "今天先做哪些订单？" | 交期/客户等级/库存/设备负载综合排序 |
| 订单详情 | "ORD001 能按时交付吗？" | 状态/材料/设备 |
| 紧急与瓶颈 | "有哪些紧急订单？哪些设备是瓶颈？" | 资源负载分析 |
| 客户评估 | "东莞模具厂信用如何？" | 客户数据 + 建议 |
| 库存影响 | "PEEK 材料够吗？影响哪些订单？" | 库存联动分析 |
| 合同条款（RAG） | "广州航天合同有什么特殊条款？" | 混合检索 + 重排命中合同原文 |

**真实业务约束**（制造业特有，非玩具）：
- 单材料约束（一个订单指定材料）、坏件口径、耗料公式由规则引擎计算（不交 LLM）
- 合同赔付、航天件全检等业务细节（访谈真实需求而来）
- 验证结论：**团队级验证**（非规模化），以 3D 打印/CNC 排程排产为载体

---

## 二、技术架构

**分层结构**（`demo/` 目录）：

```
入口层     main.py（CLI） · api.py（FastAPI 网关 /ask /health /threads/{id}/history）
配置层     config.py（单一 PROVIDERS 注册表，主备 fallback 单一事实源）
基座层     core/llm_client.py（统一 call_llm + 主备降级 + 连接池 + L1 精确缓存）
缓存层     cache/llm_cache.py（L1 精确缓存 SQLite）· semantic_cache.py（L2 语义缓存 Chroma）
工具层     tools/registry.py（ToolRegistry O(1) 查找 + 参数白名单 + RBAC 强制 + tracer 接入）
           order_tools / resource_tools / data（CSV）· mcp_servers.py（FastMCP 展示）
RAG 层     rag/retriever.py（BM25+向量+RRF+Cross-Encoder 混合检索）· knowledge_base.py
编排层     graph/single_agent_graph.py（LangGraph 状态图 + SqliteSaver checkpointer）
Agent 层   agents/single_agent.py · router.py · review_agent.py · production_agent.py · supervisor.py
权限层     auth/token_exchange.py（STS，RFC 8693）· guard.py（RBAC）· audit_logger.py
观测层     observability/tracer.py（Span，OTel 同构）· exporter.py（console/otel/OTLP）
```

**Harness 三层对应**：
- 编排层 = `graph/` + `agents/`（LangGraph 状态机驱动 Agent 循环）
- 权限层 = `auth/`（STS 令牌交换 + RBAC 守卫 + 审计，洋葱型三道防线）
- 观测层 = `observability/`（Span 全链路追踪，OTel 同构接口）

**双运行模式**：
- **单 Agent**：一个 Agent + 工具注册表，LangGraph 状态图编排（分析→选工具执行→评估→生成）
- **多 Agent（Supervisor）**：主管路由问题到专业子 Agent（订单评审/生产评估），子 Agent 各持受限权限令牌，主管汇总，带 RBAC 鉴权 + 审计日志

**部署形态**：本地 `python -m demo.main` → FastAPI HTTP 网关 → Docker 容器（Dockerfile + compose，`DEMO_RUNTIME_DIR` 分离运行时数据与业务数据，卷持久化）。

---

## 三、业务流程

**单 Agent 流程**（LangGraph 状态图）：
```
用户提问 → analyze_intent（意图识别）
        → select_and_execute（LLM 决策调哪些工具 → 执行 → 注入 tool 结果）
        → evaluate_results（评估是否足够）
        → should_continue 条件边：末条是 tool 结果→继续循环；是 assistant 文本→generate_answer
        → generate_answer → END
安全阀：迭代 ≥5 轮强制结束（防死循环）
```

**多 Agent 流程**（Supervisor 调度）：
```
用户提问 → 意图路由（router 关键词：review/production/full/query）
        → STS 签发用户 Token → 交换子 Agent 受限 Token（reviewer/scheduler，5min TTL）
        → 分派 review_agent（订单详情/生产状态/客户 权限）
        → 分派 production_agent（全工具权限）
        → 子 Agent 工具调用经 registry 走 RBAC（无权拒绝 + 审计）
        → LLM 汇总综合回答
```

**RAG 混合检索流程**：
```
向量召回（Chroma/MiniLM） + BM25（jieba 分词）
        → RRF 融合（Reciprocal Rank Fusion，两路排名 1/(k+rank) 累加）
        → Cross-Encoder 重排（BAAI/bge-reranker-base，精排 top3）
        → 命中合同原文返回
为什么混合：纯向量中文召回弱（top1 常召回错误文档），BM25 补关键词字面命中（"广州航天"必须命中）
```

**LLM 调用流程**（成本控制）：
```
语义缓存（L2，近义问题命中跳过整图执行，~50ms）→ 未命中
  → L1 精确缓存（相同 prompt 命中 <1ms，0 token）→ 未命中
  → call_llm（遍历 PROVIDERS，主备顺序第一个成功即返回，失败自动降级）
```

---

## 四、技术难点与解法

| # | 难点 | 解法 | 面试讲法 |
|---|------|------|---------|
| 1 | **纯向量中文召回弱**：MiniLM top1 常召回"历史延期记录"而非目标合同 | 混合检索四步：向量 + BM25(jieba) + RRF 融合 + Cross-Encoder 重排，目标合同 top1、rerank 分 >0.9 | "中文 RAG 不能只靠向量，我加了 BM25 补字面命中 + 重排精排" |
| 2 | **reranker 离线加载卡死**：HF 未缓存时 HEAD 检查每个要等 Windows TCP 超时 ~21s ×5 retry | 直接 patch `huggingface_hub.constants`（import 时固化 HF_HUB_OFFLINE，运行时设 env 无效）；离线优先，未缓存才走代理下载 | "环境变量在 import 后被固化，必须 patch constants 才能跳过联网检查" |
| 3 | **多 Agent 越权风险**（原 week4 无鉴权） | STS Token Exchange(RFC 8693)：父令牌→受限子令牌（5min TTL，权限收缩校验防提权）；RBAC 在工具层强制（洋葱第 3 层）；审计日志 trace_id 贯穿 | "子 Agent 持受限令牌，工具层强制 RBAC，权限不能超过父令牌" |
| 4 | **主备切换散落**：week1/2/3 各维护一份 PROVIDERS | config.py 单一事实源 + 统一 `call_llm(messages, tools)` 签名 + provider 级 httpx 连接池（10 连接/provider，keep-alive 60s） | "改主备只动一处列表，调用方不感知切 provider" |
| 5 | **LLM 成本**：Agent 单轮可能 3-5 次 LLM 调用 | L1 精确缓存（SQLite <1ms 0 token）+ L2 语义缓存（Chroma cosine，阈值 0.20 校准）+ 成本跟踪 + 预算熔断 | "两级缓存 + 成本熔断，工程化控制 token 消耗" |
| 6 | **多轮上下文与重启恢复** | LangGraph SqliteSaver checkpointer（`--chat --thread` 跨进程恢复）；显式从 checkpoint 取历史，保持 dict 消息格式（避免 add_messages 转对象类型风险） | "状态落盘 SQLite，重启能续上会话" |
| 7 | **可观测**：业务代码在 span 结束后才写 token 属性，立即导出会丢 | 自研轻量 Tracer（Span/trace_id，OTel 同构接口）+ 可插拔导出 backend（none/console/otel/OTLP 发 Jaeger）+ 延迟批量导出（整轮 query 结束才 flush） | "OTel 同构最小实现，week5 换 backend 不动业务代码" |
| 8 | **工具安全**：LLM 可能传多余字段/越权调工具 | ToolRegistry：O(1) 字典查找 + 参数白名单过滤（只传 Schema 定义字段）+ RBAC 强制 + tracer 自动埋点 | "注册中心替代 if/elif 链，白名单 + RBAC 双重约束" |
| 9 | **Windows 控制台 GBK 乱码** | 包入口重配 stdout UTF-8 | — |
| 10 | **容器化部署**：模型缓存/运行时数据/网络镜像 | FastAPI 网关（/health /ask /threads/{id}/history）+ Dockerfile（清华源 torch CPU）+ compose（HF_ENDPOINT hf-mirror 加速、`DEMO_RUNTIME_DIR` 运行时卷分离、模型缓存挂载） | "CLI → HTTP 网关 → 容器化，交付闭环" |

---

## 五、亮点（面试弹药）

1. **单/多 Agent 双模式**：一套代码两种编排（LangGraph 状态图 + Supervisor 调度），按问题复杂度切换
2. **Harness 三层完整落地**：编排-权限-观测，行业推荐架构的教学级完整实现
3. **权限设计真实落地**：RFC 8693 Token Exchange（非玩具）+ 洋葱型防御三道防线（网关/运行时/工具层）+ 审计 trace_id 贯穿
4. **观测 OTel 同构**：可插拔 backend（console/otel/OTLP），无侵入接 Jaeger，换 backend 不动业务代码
5. **两级缓存 + 成本熔断**：L1 精确 <1ms 0 token、L2 语义 ~50ms，工程化成本控制
6. **状态持久化**：SqliteSaver 跨进程恢复多轮对话
7. **交付闭环**：CLI → FastAPI 网关 → Docker 容器化，生产化路径完整

---

## 六、口径红线（对面试官）

- 术语锚点可深可浅：VP/CTO 问"Agent 到什么深度"→ 讲 4-7 行全链路（ReAct→LangGraph→Supervisor→Token Exchange→RAGAS）；HR/猎头不问不主动展开
- 说"团队级验证"不说"规模化"（demo 是验证可行性，非生产规模）
- 源码可追溯：`agent-training/demo/` + `agent-training/scripts/week1-4/`（repo 备索）
