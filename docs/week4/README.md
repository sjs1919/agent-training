# Week4：Week1/Week2 补缺

> **定位**：本目录不推进新进度，专门补 Week1、Week2 走读时跳过/未展开的理论点与配套代码。
> 每份文档/脚本都标注了它补的是 week1 还是 week2 的哪块缺口。
>
> **起因**：Week3 代码走读（7/23）后发现，week1/week2 代码跑通了，但"会调 API/会跑 RAG"和"讲得透原理"之间还有一层工程化知识没补。本目录集中填这层。

---

## 文档（理论补缺）

| 文件 | 补谁的缺 | 内容要点 |
|------|---------|---------|
| `docs/week4/补缺_week1_API与Prompt.md` | Week1 | tool_choice 四档 / Structured Outputs(strict) / 流式 / Prompt Caching / Reasoning 模型提示 / Namespaces / Prompt Injection 防护 / ReAct / 上下文压缩 / 重试策略代码 |
| `docs/week4/补缺_week2_RAG.md` | Week2 | RAG 三大范式 / Embedding 选型 / 分块策略 / Milvus 选型 / RAGAS 4 指标理论 / **Agentic RAG 4 模式选型表** / Filesystem+Subagents / 幻觉 mitigation |

阅读顺序：先 week1 补缺（API 工程化），再 week2 补缺（RAG 工程化）。两份文档的小结章节都画了知识关系图，可先看图再回头读细节。

---

## 脚本（配套代码）

| 文件 | 对应理论 | 复用 week2 | 说明 |
|------|---------|-----------|------|
| `scripts/week4/ragas_eval.py` | week2 补缺 §5 RAGAS | `call_with_fallback` + `rag_answer_hybrid` + 建库三件套 | 手写实现 4 指标（faithfulness/answer_relevancy/context_precision/context_recall），LLM-as-Judge，5 个合同 ground truth |
| `scripts/week4/rubric_checked_rag.py` | week2 补缺 §6 模式② | `retrieve_hybrid` + `RAG_SYSTEM_PROMPT` | Agentic RAG 模式②落地：生成->Grader 按 Rubric 打分->不达标反馈重生成循环，对比 week2 基线 |

两脚本都通过 `sys.path.insert` 引入 week2（与 day2 引 day1 同套路），不重写检索/LLM 逻辑。运行前确保 week2 的向量库已建好（首次跑 week2 脚本会自动建）。

---

## 与原 week1/week2 文档的关系

- week1 原理论：`docs/week1/day4_guide.md` + `week1_串讲总结.md`（讲了的）-> 本目录补**没讲的**。
- week2 原理论：`docs/week2/day1_guide.md` + `day4_guide.md` + `week2_代码深度解读.md` -> 本目录补**没讲的**。
- week3 的 LangChain/LangGraph 理论：`docs/week3/langchain_langgraph_理论.md`（已独立补完，不在本目录）。

---

## 运行

```bash
# 在 projects/agent-training 下
python scripts/week4/ragas_eval.py          # 跑 RAGAS 评估，输出 4 指标配平均分
python scripts/week4/rubric_checked_rag.py  # 跑 Rubric-checked，对比 week2 基线
```

输出明细落 `tmp/`（不入 Git）。两脚本首次运行会加载 week2 向量库 + BM25 + bge-reranker（离线优先，已缓存秒载）。
