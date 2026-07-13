# 第二周 Day 1 学习指南 - RAG 基础层

> **日期**：2026-07-13（周一）
> **知识块**：⑤ RAG 检索增强
> **产出**：`scripts/week2/day1_rag_basics.py`
> **一句话**：让模型"知道"你的私有数据（合同、延期记录），不再凭空编造。

## 今日目标

搭起端到端 RAG 骨架，理解 RAG 三步流程：

```
用户问题 → [转向量] → 在文档向量里找 top-k 最相似片段 → [喂给 LLM] → 基于片段回答
```

跑通后，模型能回答"延期赔付怎么算""加急订单有什么规定"这类**只存在于你私有文档里**的问题。

## 依赖安装

```bash
pip install chromadb
```

只需一个包。Chroma 自带默认 Embedding 模型（ONNX 版 all-MiniLM-L6-v2），免装 torch，开箱即跑。

> 首次运行会下载 ONNX 模型（约 80MB）到用户目录，之后离线可用。

主备 provider 沿用 week1（豆包 + DeepSeek），`.env` 已配好，无需改动。

## 跑起来

```bash
cd projects/agent-training
python scripts/week2/day1_rag_basics.py
```

首次跑：加载 4 个文档（3 份合同 + 历史延期记录）→ 分块 → 向量化 → 灌入 Chroma（持久化到 `scripts/week2/data/chroma_db/`）。
之后再跑直接复用，秒级进入检索演示。

## RAG 五个核心知识点

| # | 知识点 | 一句话 | 在代码里 |
|---|--------|--------|---------|
| 1 | 向量嵌入 Embedding | 文本 → 一串数字，语义相近则向量相近 | Chroma 自动调 embedding |
| 2 | 相似度检索 | 找向量最近邻（余弦距离） | `collection.query()` |
| 3 | top-k 检索 | 取最相似的 k 条 | `n_results=top_k` |
| 4 | 索引 ANN | 为加速建的数据结构，牺牲一丝精度换速度 | Chroma 内部用 HNSW |
| 5 | 为何不用 MySQL | SQL 只能精确匹配，查不了语义 | — |

**语义检索的威力**：你问"延期赔付"，能检索到写着"逾期赔偿约定"的段落--字面不同、语义相同。MySQL 的 `LIKE '%延期%'` 查不到"逾期"。

## Embedding 选型

| 模型 | 体积 | 中文效果 | 安装 |
|------|------|---------|------|
| all-MiniLM-L6-v2（默认） | 80MB | 一般 | 装 chromadb 即带 |
| **bge-small-zh-v1.5**（推荐升级） | 95MB | 好 | 额外装 sentence-transformers |
| bge-m3 / qwen3-embedding | 较大 | 更好 | 持续关注新模型 |

**今天用默认**：先跑通管线，理解流程比调优 embedding 重要。
**升级方法**：见 `day1_rag_basics.py` 第二部分注释，换一行 `embedding_function` 即可。

```bash
pip install sentence-transformers   # 升级 bge 前先装
```

## 分块策略

文档太长不能整篇塞进检索，要先切块。分块直接影响召回率：

| 策略 | 说明 | 召回 | 复杂度 |
|------|------|------|--------|
| 固定字符切分（今天用） | 每 500 字一块，重叠 100 字 | 基准 | 最简 |
| 固定 token 切分 | 用 tiktoken 按 token 切 | 基准 | 简 |
| RecursiveCharacterTextSplitter | 按段落>句子>字符层级切，保语义 | 较好 | 中（LangChain） |
| 语义切分 SemanticChunker | 按 embedding 相似度断句 | 最好（0.67→0.91） | 高 |

**为什么重叠**：硬切会切断语义（如"赔付比例"被切成"赔付"和"比例"），重叠 100 字让边界内容在相邻块都出现，保住完整性。

清单建议 1024 token + 100 overlap；今天用字符近似（中文 1 字 ≈ 1.5-2 token，500 字 ≈ 近 1024 token）。

## 代码结构

`day1_rag_basics.py` 三部分：

1. **知识库加载 + 分块**：`load_documents()` 读 txt，`chunk_text()` 切块
2. **Chroma 向量库**：`get_or_build_vectorstore()` 灌入/复用，`retrieve()` top-k 检索
3. **端到端 RAG**：`rag_answer()` 检索 + LLM 生成

provider 主备架构（`PROVIDERS` + `call_with_fallback`）沿用 week1 day1，`httpx.Client(trust_env=False)` 绕系统代理的坑已处理。

## 预期输出（关键节点）

```
🚀 第二周 Day 1：RAG 基础层
可用 provider: 火山豆包(coding), DeepSeek

第一部分：构建向量库
  📥 首次构建向量库：加载文档 -> 分块 -> 向量化 -> 灌入
  ✅ 灌入 N 个文本块（来自 4 个文档）

第二部分：纯检索演示
  🔎 '延期赔付怎么算' -> top 2:
    [1] 深圳精密五金_合同特殊条款.txt (距离 0.xxxx)

第三部分：端到端 RAG
  🔍 检索：客户订单延期了，要怎么赔付？
  💬 回答：根据《深圳精密五金_合同特殊条款》第三条，逾期每日按 0.5% 赔付...
```

## 练习（巩固）

1. **换 bge-small-zh**：装 sentence-transformers，按注释换 `embedding_function`，对比同一 query 的 distance 变化（应更小=更相似）
2. **调分块参数**：把 `chunk_size` 改 300 / 800，看召回质量变化
3. **对比无 RAG**：把 `rag_answer` 里的检索片段去掉，直接问 LLM"深圳精密五金的延期赔付比例"--看它是否编造（大概率会瞎说）
4. **加文档**：往 `data/contracts/` 再放一份 txt，删 `chroma_db/` 重建，看新文档能否被检索

## 踩坑预警

- **chromadb 首次下载 ONNX 慢**：国内网络可能慢，耐心等；若卡死设镜像或离线装
- **Windows 编码**：已 `sys.stdout.reconfigure(encoding="utf-8")`，开箱即跑
- **系统代理残留**：已 `trust_env=False`，cc-switch 退出后仍能直连（详见 [[cc-switch 启动模式]]）
- **向量库脏数据**：改了文档或 embedding 后，删 `data/chroma_db/` 重建

## 下一步

Day 2（周二）：在 day1 基础上加**混合检索**（BM25 + 向量 RRF 融合）+ **Cross-Encoder 重排序**，把召回/精确率打到生产可用。
