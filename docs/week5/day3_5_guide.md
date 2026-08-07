# 第五周 Day3-5 — 缓存 + 持久化 + 容器化 + Agent 评估

> **对应代码**：`cache/` · `graph/checkpointer.py` · `auth/`（持久化补齐）· `api.py` · `Dockerfile`
> **对应文档**：`docs/courses/Agent评测漫谈*.md` · `demo-缺陷漏洞与知识盲区分析.md`

---

## 先看清全貌：Week 5 在 Week 4 基础上新增了什么

```
Week 4 架构                     Week 5 架构
─────────────                   ─────────────
Supervisor + 子 Agent            Supervisor + 子 Agent（不变）
       │                              │
       ├── 鉴权层                      ├── 鉴权层（+ 持久化）
       │   Token 内存存储              │   Token SQLite 持久化
       │   审计 内存列表               │   审计 JSONL 落盘
       │                              │
       │                              ├── 观测层（Day 1-2 已讲）
       │                              │   tracer + exporter + cost
       │                              │
       │                              ├── 缓存层（新增 ⭐）
       │                              │   L1 精确 + L2 语义
       │                              │
       │                              ├── 持久化层（新增 ⭐）
       │                              │   checkpointer + token + audit
       │                              │
       ▼                              ├── 部署层（新增 ⭐）
MCP 工具层                        │   FastAPI + Docker
                                  ▼
                             MCP 工具层（不变）
```

---

## Day 3：缓存 + 状态持久化

### 1. 为什么需要缓存？

每次 LLM 调用都有成本（token + 延迟）。很多场景下，相同或相似的问题不需要重复调 LLM：

| 场景 | 无缓存 | 有缓存 |
|------|--------|--------|
| 用户重复问同一个问题 | 重新调 LLM，2500 tokens，3s | L1 命中，0 tokens，<1ms |
| 用户换种说法问（"今天排产"→"今天先做哪些"） | 重新调 LLM | L2 语义命中，0 tokens，~50ms |
| 多轮对话中追问 | 每轮都调 LLM | 检查点恢复上下文，只调增量 |

### 2. 两级缓存架构

```
用户问题
    │
    ▼
┌─────────────────┐
│  L1 精确缓存     │  SQLite，cache_key = hash(prompt)
│  相同 prompt？   │  命中：<1ms，0 token
└────┬────────────┘
     │ miss
     ▼
┌─────────────────┐
│  L2 语义缓存     │  Chroma cosine
│  近义改写？      │  命中：~50ms，0 token
└────┬────────────┘
     │ miss
     ▼
  调 LLM（正常流程）
     │
     ▼
  结果写入 L1 + L2
```

### 3. L1 精确缓存（`cache/llm_cache.py`）

**原理**：把 (prompt_hash, response) 存 SQLite，相同 prompt 直接返回。

```python
class LLMCache:
    def get(self, cache_key: str) -> tuple[str | None, bool]:
        # SQLite 查询，O(1)
        # 命中返回 (response, True)，未命中返回 (None, False)

    def put(self, cache_key: str, response: str) -> None:
        # 写入 SQLite
```

**集成点**：`core/llm_client.py` 的 `call_llm()` 在调 LLM 前先查 L1：

```python
def call_llm(messages, tools=None):
    cache_key = _make_cache_key(messages, tools)
    cached, hit = llm_cache.get(cache_key)
    if hit:
        return cached  # 0 token，<1ms
    # ... 正常调 LLM ...
    llm_cache.put(cache_key, response)
    return response
```

### 4. L2 语义缓存（`cache/semantic_cache.py`）

**原理**：用 Chroma 的 cosine 空间，找语义相似的问题。threshold 0.20 以下算命中。

```python
class SemanticCache:
    def lookup(self, query: str, threshold: float = 0.20) -> tuple[str | None, float | None]:
        # Chroma cosine 查询
        # distance < threshold → 命中，返回 (answer, distance)

    def put(self, query: str, answer: str) -> None:
        # 写入 Chroma collection
```

**关键限制**：语义缓存只对 `thread_id=None` 的独立问题生效。多轮对话依赖前文上下文，首轮缓存的结果不包含后续上下文，复用会导致回答不连贯。

**阈值校准**：

| 测试 | cosine distance | 结果 |
|------|----------------|------|
| 同义改写（"今天排产" vs "今天先做哪些"） | 0.17 | ✅ 命中 |
| 不相关问题 | 0.46+ | ❌ 未命中 |
| 默认阈值 0.20 | — | 正好分隔 |

**环境变量**：`SEMANTIC_CACHE=on[默认]/off`、`CACHE_THRESHOLD=0.20`

### 5. 状态持久化（`graph/checkpointer.py`）

**为什么需要**：Week 4 的 Agent 状态全在内存，进程退出就丢失。多轮对话需要"记住"上下文。

**实现**：LangGraph 的 checkpointer 机制，编译图时传入：

```python
# 编译时接入
graph = builder.compile(checkpointer=build_checkpointer())

# 运行时指定 thread_id
result = graph.invoke(input, config={"configurable": {"thread_id": "user_001"}})
```

**三种 backend**：

| `CHECKPOINTER` | 行为 | 用途 |
|---|---|---|
| `sqlite`（默认） | 落盘 `demo/data/checkpoints.db` | 默认，真持久化 |
| `memory` | 进程内存 | 仅演示概念 |
| `none` | 无检查点 | 等价 week4 |

**多轮对话**：`--chat` 模式启动 REPL，每轮用同一个 thread_id，从 checkpoint 取历史 messages 追加：

```bash
python -m demo.main --chat
# > 今天有哪些紧急订单？
# Agent: ...（5 个紧急订单）
# > 其中哪些材料不够？
# Agent: ...（记住上一轮的上下文，继续分析）
```

**跨进程恢复**：`--thread <id>` 续接之前的对话：

```bash
# 进程 1
python -m demo.main --chat --thread user_001
# > 问了几个问题后退出

# 进程 2（重启后）
python -m demo.main --chat --thread user_001
# > 继续之前的对话，上下文不丢
```

---

## Day 4：持久化补齐 + 容器化

### 1. Token 持久化（`auth/token_exchange.py`）

Week 4 的 Token 存内存字典，重启丢失。Week 5 补齐：

```python
# TokenStore 抽象
class TokenStore(Protocol):
    def save(self, token: Token) -> None: ...
    def load(self, token_id: str) -> Token | None: ...
    def revoke(self, token_id: str) -> None: ...
    def revoke_all(self) -> None: ...

# SQLite 实现（默认）
class SqliteTokenStore:
    """Token 落盘到 {RUNTIME_DIR}/tokens.db，重启可恢复。"""

# 内存实现（可切回）
class MemoryTokenStore:
    """等价 Week 4 行为。"""
```

**环境变量**：`TOKEN_STORE=sqlite[默认]/memory`

### 2. 审计持久化（`auth/audit_logger.py`）

Week 4 的审计日志存内存列表。Week 5 补齐 JSONL 落盘：

```python
class AuditLogger:
    def log(self, action, subject, target, ...):
        entry = {...}
        self._entries.append(entry)
        self._persist(entry)  # 即时追加到 JSONL 文件

    def _persist(self, entry):
        """追加写入 {RUNTIME_DIR}/audit.jsonl，每行一条 JSON。"""
```

**环境变量**：`AUDIT_LOG=jsonl[默认]/none`

### 3. FastAPI 网关（`api.py`）

把 demo 从"命令行脚本"升级为"HTTP 服务"：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/ask` | POST | 提交问题，返回 Agent 回答 |
| `/health` | GET | 健康检查 |
| `/threads/{id}/history` | GET | 查看对话历史 |

```python
@app.post("/ask")
async def ask(request: AskRequest):
    # request.question + request.thread_id + request.mode
    result = run_agent(request.question, ...)
    return {"answer": result, "thread_id": request.thread_id}
```

### 4. Docker 容器化

**Dockerfile 要点**：
- 基础镜像：`python:3.11-slim`
- CPU 版 torch（精简依赖，不含 GPU）
- `requirements-demo.txt`（demo 专用，不含 akshare/pandas/adk/litellm）
- 模型缓存挂载（reranker + embedding 不随镜像）

**docker-compose.yml 要点**：
- 模型缓存卷：`~/.cache/chroma` + `~/.cache/huggingface`
- 运行时数据卷：`./demo/data` → `/app/demo/data`
- 端口映射：`8000:8000`

**当前状态**：代码已提交，Docker Desktop 引擎未启动，待验收。

---

## Day 5：Agent 评估 + 业务匹配 + 缺陷分析

### 1. Agent 评估 ≠ 只看结果

传统模型评测回答"算得准不准""模型能力强不强"。Agent 评测要回答：

> 当模型被放进一个真实系统里，和 Prompt、Skill、工具链、记忆、状态管理、业务流程耦合在一起后，它能不能稳定交付好的结果。

**两种评估维度**：

| 维度 | 关注 | 方法 |
|------|------|------|
| **Response Evaluation** | 最终输出好不好 | 人工评分 / LLM-as-Judge / 自动指标 |
| **Trajectory Evaluation** | 过程对不对 | 检查 Agent 是否走了正确的步骤、调了正确的工具 |

**核心公式**：**观测 + 评测 = 持续迭代**

- 没有观测 → 没有数据 → 无法评估
- 没有评估 → 不知道哪里好哪里差 → 无法迭代
- 没有迭代 → Agent 永远停在 Demo 水平

### 2. 业务匹配度：什么时候该用 Agent？

不是所有场景都值得用 Agent。判断框架：

| 场景特征 | 推荐方案 | 例子 |
|---------|---------|------|
| 固定流程、输入输出确定 | **Workflow**（硬编码流程） | 订单状态查询、库存检查 |
| 需要灵活判断、多步推理 | **Agent**（自主决策） | 排产优先级、合同条款解读 |
| 简单问答、知识检索 | **RAG**（检索增强） | "XX 合同有什么条款？" |
| 纯文本生成、无需工具 | **Prompt**（直接调 LLM） | 邮件草稿、报告摘要 |

**demo 的匹配度分析**：

| demo 功能 | 匹配方案 | 理由 |
|----------|---------|------|
| 查订单/库存/设备 | Workflow 更合适 | 输入输出确定，不需要推理 |
| 排产优先级排序 | Agent 合适 | 需要多维度综合推理 |
| 合同条款检索 | RAG 合适 | 知识检索，不需要决策 |
| 多 Agent 协作评审 | Agent 合适 | 需要跨领域信息综合 |

### 3. demo 缺陷排查（对照课程三梯队）

> 详见 `docs/courses/demo-缺陷漏洞与知识盲区分析.md`

**核心增量盲区（🔴 严重）**：

| 盲区 | 现状 | 差距 |
|------|------|------|
| 工具执行沙箱与重试 | `registry.execute` 无重试 | API 超时直接抛异常，无指数退避 |
| 上下文压缩 | 无 | messages 无限增长，长轮对话无截断 |
| 输出护栏（guardrails） | 无 | 无 JSON 格式校验、越权指令过滤 |
| 步骤校验 | `evaluate_results` 是 noop | 模型可能 hallucinate 工具结果 |

**新视角补强盲区（🟡 中等）**：

| 盲区 | 现状 | 差距 |
|------|------|------|
| 业务数据包 | CSV 分散，工具函数直接读 | 未按"问答/筛选/推荐/流程"四类场景组织 |
| Prompt 版本管理 | `system_prompts.py` 硬编码 | 无 A/B 测试基础 |
| SLA 定义 | 无 | 无"排产建议 < 3s"等 SLA |
| 单 Agent 绕过鉴权 | `token=None` 完全绕过 RBAC | 无"强制鉴权模式"开关 |

### 4. Week 5 完成度评估

| 维度 | 完成度 | 说明 |
|------|--------|------|
| 全链路追踪 | 高 | Span + 可插拔导出 + OTel 同构 |
| 成本监控 | 高 | 定价计费 + 预算熔断 + 预警 |
| 缓存 | 高 | L1 精确 + L2 语义两级 |
| 状态持久化 | 高 | SqliteSaver + 多轮 + 重启恢复 |
| Token/审计持久化 | 高 | SQLite + JSONL 落盘 |
| 容器化 | 中 | 代码完成，Docker 环境待验收 |
| Agent 评估 | 中 | 课程笔记 + 缺陷分析完成，缺评估脚本 |
| 业务匹配 | 中 | 框架理解完成，缺 SLA 定义 |
| **整体** | **中高** | 工程化深度超额，评估/SLA 有缺口 |

---

## 学习路径

```
上午 · 理论消化
  ├─ Day 3：两级缓存 + 状态持久化
  │  代码对照：cache/ + graph/checkpointer.py
  ├─ Day 4：持久化补齐 + 容器化
  │  代码对照：auth/（持久化部分）+ api.py + Dockerfile
  └─ Day 5：Agent 评估 + 业务匹配 + 缺陷分析
     文档对照：docs/courses/ 两个课程文档

下午 · 编码 + 验证
  ├─ 跑 python -m demo.main --check 确认地基
  ├─ 跑 python -m demo.main --chat 体验多轮 + 持久化
  ├─ OTEL_EXPORTER=console 跑一次看 trace 导出
  ├─ LLM_BUDGET_LIMIT=0.01 跑一次看预算熔断
  └─ 对照缺陷清单，标记 Week 6 可补项
```

---

## 核心认知（Day3-5 最重要的 5 句话）

1. **两级缓存 = 降本 + 降延迟** — L1 精确缓存 0 token，L2 语义缓存跳过整图执行，命中时用户无感
2. **语义缓存只对独立问题生效** — 多轮对话依赖前文，首轮缓存不含后续上下文，复用会不连贯
3. **持久化 = 从 Demo 到产品** — 内存状态重启即失，SQLite 持久化让 Agent 真正"记住"上下文
4. **Agent 评估看过程不只看结果** — Trajectory Evaluation（过程对不对）比 Response Evaluation（结果好不好）更能指导迭代
5. **不是所有场景都该用 Agent** — 固定流程用 Workflow，知识检索用 RAG，简单生成用 Prompt，只有需要灵活推理才用 Agent

---

## 参考资料

| 知识块 | 资料 |
|--------|------|
| ⑩ 可观测性（缓存） | [GPTCache 语义缓存](https://github.com/zilliztech/GPTCache) · [LangGraph 持久化](https://langchain-ai.github.io/langgraph/concepts/persistence/) ⭐ |
| ⑪ 业务匹配 | [Anthropic When to use agents](https://docs.anthropic.com/en/docs/agents-and-tools) ⭐ · [Agent 评估体系 — 美团图灵](https://mp.weixin.qq.com/s/gZKWRqznB8sNBFf69fBIvw) ⭐ · [RAGAS 评估框架](https://docs.ragas.io/) |
| 部署 | [FastAPI 部署指南](https://fastapi.tiangolo.com/deployment/docker/) · [Docker Compose](https://docs.docker.com/compose/) |
