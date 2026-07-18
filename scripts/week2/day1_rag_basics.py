"""
第二周 · Day 1 - RAG 基础层（Embedding + 分块 + 向量库 + 检索）
==========================================================
目标：搭起端到端 RAG 骨架，让模型能"检索"你的私有数据。
      理解 RAG 三步：问题转向量 -> 在文档向量里找最相似的 top-k 段 -> 喂给模型回答。

核心认知：RAG 让大模型"知道"它训练时没见过的私有数据（合同、延期记录）。
        本质是"检索 + 生成"，模型不再凭空编造，而是基于检索到的真实片段回答。

知识块：⑤ RAG 检索增强
今日栈：Chroma 向量库（本地持久化）+ 字符分块 + Chroma 默认 Embedding + 主备 LLM
业务域：沿用 week1 的 3D 打印/CNC 调度场景（合同条款 + 历史延期记录）

[AI:Claude] 架构设计：Chroma 向量库 + 主备 fallback 复用 week1
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
import httpx

try:
    import chromadb
except ImportError:
    print("❌ 未安装 chromadb，请运行：pip install chromadb")
    sys.exit(1)

# Windows 默认 stdout 走 GBK，编码不了 emoji/部分中文 -> 切 UTF-8（开箱即跑）
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent.parent / ".env")

# ============================================================
# Provider 注册表（沿用 week1 主备架构）
# ============================================================

PROVIDERS = [
    {
        "name": "火山豆包(coding)",
        "enabled": True,
        "api_key": os.getenv("VOLC_API_KEY", ""),
        "base_url": os.getenv("VOLC_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding/v3"),
        "model": os.getenv("VOLC_MODEL", "ark-code-latest"),
        "note": "主用 · 字节编程套餐",
    },
    {
        "name": "DeepSeek",
        "enabled": True,
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "note": "备用1 · ¥1/百万Token",
    },
    {
        "name": "Kimi(coding)",
        "enabled": os.getenv("KIMI_ENABLED", "false").lower() == "true",
        "api_key": os.getenv("KIMI_API_KEY", ""),
        "base_url": os.getenv("KIMI_BASE_URL", "https://api.kimi.com/coding/v1"),
        "model": os.getenv("KIMI_MODEL", "kimi-for-coding"),
        "note": "备用2 · 会员过期暂禁用",
    },
]


def _is_real_key(key: str) -> bool:
    return bool(key) and "your-" not in key.lower()


def call_llm(provider, system_prompt, user_prompt, max_tokens=500, temperature=0.3):
    """用指定 provider 调用一次 LLM（沿用 week1）"""
    if not provider.get("enabled"):
        raise RuntimeError(f"provider {provider['name']} 已禁用")
    if not _is_real_key(provider["api_key"]):
        raise RuntimeError(f"provider {provider['name']} key 未配置")
    client = OpenAI(
        api_key=provider["api_key"],
        base_url=provider["base_url"],
        http_client=httpx.Client(trust_env=False),  # 绕过系统/注册表代理直连
    )
    response = client.chat.completions.create(
        model=provider["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response, provider


def call_with_fallback(system_prompt, user_prompt, max_tokens=500, temperature=0.3):
    """主备 fallback（沿用 week1）：按序逐个试，第一个成功即返回"""
    log = []
    last_err = None
    for p in PROVIDERS:
        if not p.get("enabled"):
            log.append(f"  ⏭️  {p['name']:18s} 跳过（已禁用）")
            continue
        if not _is_real_key(p["api_key"]):
            log.append(f"  ⏭️  {p['name']:18s} 跳过（key 未配置）")
            continue
        try:
            resp, used = call_llm(p, system_prompt, user_prompt, max_tokens, temperature)
            log.append(f"  ✅  {p['name']:18s} 成功")
            return resp, used, log
        except Exception as e:
            last_err = e
            log.append(f"  ❌  {p['name']:18s} 失败: {type(e).__name__}: {str(e)[:80]}")
    raise RuntimeError(f"所有 provider 均失败。最后错误: {last_err}\n日志:\n" + "\n".join(log))


# ============================================================
# 第一部分：知识库加载 + 分块
# 导航：阅读导航_week1_week2.md → Week2 周一 → "分块策略（语义 > 固定）"
# 知识：RAG 管线第一步：将原始文档切成可检索的片段
#       分块策略影响 Recall：固定字符切分 → 语义切分(0.67→0.91)
#       生产环境：RecursiveCharacterTextSplitter (按段落>句子>字符层级)
#                 或 SemanticChunker (按 embedding 相似度断句)
# ============================================================

DATA_DIR = Path(__file__).parent / "data"
CONTRACTS_DIR = DATA_DIR / "contracts"


def load_documents():
    """加载知识库文档：历史延期记录 + contracts/ 下所有合同 txt"""
    docs = []  # [(filename, text), ...]
    delay_file = DATA_DIR / "历史延期记录.txt"
    if delay_file.exists():
        docs.append((delay_file.name, delay_file.read_text(encoding="utf-8")))
    for f in sorted(CONTRACTS_DIR.glob("*.txt")):
        docs.append((f.name, f.read_text(encoding="utf-8")))
    return docs


def chunk_text(text, chunk_size=500, overlap=100):
    """
    字符级分块：按 chunk_size 切，相邻块重叠 overlap 字符。

    【原子操作】滑动窗口分块：
    start = 0 → text[start:start+chunk_size] → start += (chunk_size - overlap)
    overlap 解决"关键句子刚好被切在两块边界"的问题
    中文 1 字 ≈ 1.5-2 token，500 字 ≈ 接近 1024 token（常见 LLM context 窗口单位）

    生产升级路径（分块策略选型）：
    - 固定 token 切分（tiktoken）：模型按 token 计费，token 对齐更准
    - RecursiveCharacterTextSplitter（LangChain）：按段落>句子>字符层级切，保语义完整
    - 语义切分（SemanticChunker）：按 embedding 相似度断句，Recall 最高（0.67->0.91）
    详见：阅读导航 → Week2 周一 → "分块策略"
    """
    chunks = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(text):
        chunk = text[start : start + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
        if start + chunk_size >= len(text):
            break
        start += step
    return chunks


# ============================================================
# 第二部分：Chroma 向量库
# 导航：阅读导航_week1_week2.md → Week2 周一 → "Embedding 模型选型"
# 知识：RAG 管线第二步：分块 → Embedding → 向量库 → 可检索
#       Embedding = 文本 → 高维向量(768/1024维)，语义相似的文本向量距离近
#       选型：MiniLM(默认) → bge-small-zh(推荐) → bge-m3(多语言) → qwen3-embedding(最新)
#       Chroma 默认 all-MiniLM-L6-v2(ONNX, ~80MB, 多语言)
#       中文专用 bge-small-zh-v1.5(sentence-transformers, ~95MB, 召回明显优于MiniLM)
#       详见：阅读导航 → Week2 周一 → "RAG 端到端流程(LangChain 官方)"
# ------------------------------------------------------------
# Embedding 的认知关键：
# "加急订单" 和 "紧急订单" 在向量空间距离近（语义相似）
# "加急订单" 和 "合同编号PO-2026" 在向量空间距离远（语义无关）
# 所以向量检索擅长"找意思相近的"，不擅长"找关键词精确匹配"（那是 BM25 的领域）
# ------------------------------------------------------------

DB_DIR = DATA_DIR / "chroma_db"
COLLECTION_NAME = "kb_contracts_delay"


def get_or_build_vectorstore():
    """
    获取或构建 Chroma 向量库：
    已有数据则直接复用（持久化在 chroma_db/）；否则 加载文档 -> 分块 -> 灌入。
    """
    client = chromadb.PersistentClient(path=str(DB_DIR))
    collection = client.get_or_create_collection(COLLECTION_NAME)

    if collection.count() > 0:
        print(f"  ♻️  向量库已有 {collection.count()} 条向量，直接复用（{DB_DIR.name}/）")
        return collection

    print("  📥 首次构建向量库：加载文档 -> 分块 -> 向量化 -> 灌入")
    docs = load_documents()
    if not docs:
        raise RuntimeError(f"知识库为空，请检查 {DATA_DIR}")

    ids, texts, metas = [], [], []
    for doc_idx, (filename, text) in enumerate(docs):
        for chunk_idx, chunk in enumerate(chunk_text(text)):
            ids.append(f"doc{doc_idx}_chunk{chunk_idx}")
            texts.append(chunk)
            metas.append({"source": filename})

    collection.add(ids=ids, documents=texts, metadatas=metas)
    print(f"  ✅ 灌入 {len(ids)} 个文本块（来自 {len(docs)} 个文档）")
    return collection


def retrieve(collection, query, top_k=3):
    """
    向量检索：query 转向量 -> 在向量库找 top-k 最相似的文本块。
    返回 [{text, source, distance}]，distance 越小越相似（默认 cosine 距离）。

    【原子操作】RAG 检索的三步：
    ① 用户 query → Embedding 模型 → 向量（768/1024 维浮点数数组）
    ② collection.query(query_texts=[query]) → Chroma 内部完成向量化 + 相似度搜索
    ③ 返回 top-k 最相似的文档片段（按 cosine distance 升序）
    distance 越小越相似：0 = 完全相同，1 = 无关，2 = 语义相反
    详见：阅读导航 → Week2 周一 → "RAG 端到端流程"
    """
    results = collection.query(query_texts=[query], n_results=top_k)
    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({
            "text": doc,
            "source": meta.get("source", "?"),
            "distance": dist,
        })
    return hits


# ============================================================
# 第三部分：端到端 RAG（检索 -> 生成）
# 导航：阅读导航_week1_week2.md → Week2 整体脉络 → "RAG 数据管线"
# 知识：RAG 本质 = 检索 + 生成，不是 "把文档全塞进 context"
#       Augmented LLM = LLM + retrieval + tools + memory (Anthropic Building Effective Agents)
#       详见：阅读导航 → Week2 整体理论脉络 → "augmented LLM"
# ============================================================

RAG_SYSTEM_PROMPT = """你是 3D 打印/CNC 加工生产调度助手。
请只根据下方"检索片段"回答用户问题，不要凭空编造。
规则：
- 若检索片段中有相关条款，引用其来源文件回答
- 若检索片段中没有相关信息，明确说"知识库中未找到相关条款"
- 回答简洁专业，用中文
"""


def rag_answer(collection, query, top_k=3, verbose=True):
    """
    [AI:Claude] 端到端 RAG：
    1. 检索：query -> 向量库找 top-k 相关片段
    2. 生成：检索片段作为 context 喂给 LLM，指示基于 context 回答

    【原子操作】RAG 管线全流程：
    ① 用户 query → retrieve() → 向量库搜索 → top-k 片段
    ② 片段拼成 prompt context → 注入 RAG_SYSTEM_PROMPT
    ③ call_with_fallback() → LLM 基于片段回答，不凭空编造
    对比 Day4/5：这是 "固定 pipeline" 模式，Agent 不参与检索决策
    """
    if verbose:
        print(f"\n🔍 检索：{query}")
    hits = retrieve(collection, query, top_k=top_k)

    if verbose:
        print(f"  命中 {len(hits)} 条（distance 越小越相似）：")
        for i, h in enumerate(hits, 1):
            preview = h["text"].replace("\n", " ")[:70]
            print(f"  [{i}] 来源:{h['source']}  距离:{h['distance']:.4f}")
            print(f"      {preview}...")

    # 【原子操作】检索片段 → Prompt context 的组装格式
    # 每个片段标注来源，让 LLM 知道"哪段来自哪个文件"
    context = "\n\n".join(
        f"【片段{i}】(来源:{h['source']})\n{h['text']}"
        for i, h in enumerate(hits, 1)
    )
    user_prompt = f"检索片段：\n{context}\n\n用户问题：{query}"

    resp, used, log = call_with_fallback(RAG_SYSTEM_PROMPT, user_prompt, max_tokens=500)
    if verbose:
        for line in log:
            print(line)
    return resp.choices[0].message.content, hits, used


# ============================================================
# 演示
# ============================================================

def demo():
    print("=" * 60)
    print("第一部分：构建向量库")
    print("=" * 60)
    collection = get_or_build_vectorstore()

    print(f"\n{'=' * 60}")
    print("第二部分：纯检索演示（不调 LLM，看向量库召回什么）")
    print(f"{'=' * 60}")
    probe_queries = ["延期赔付怎么算", "航天件质检要求", "加急订单"]
    for q in probe_queries:
        hits = retrieve(collection, q, top_k=2)
        print(f"\n🔎 '{q}' -> top 2:")
        for i, h in enumerate(hits, 1):
            print(f"  [{i}] {h['source']} (距离 {h['distance']:.4f})")

    print(f"\n{'=' * 60}")
    print("第三部分：端到端 RAG（检索 + LLM 生成）")
    print(f"{'=' * 60}")
    queries = [
        "客户订单延期了，要怎么赔付？赔付比例是多少？",
        "加急订单有什么特殊规定？加急费怎么收？",
        "航天精密件的质检要求是什么？不合格怎么处理？",
        "历史上有哪些订单延期的案例？主要原因是什么？",
    ]
    for q in queries:
        print(f"\n{'─' * 60}")
        answer, hits, used = rag_answer(collection, q)
        print(f"\n💬 回答（provider: {used['name']}）：")
        print(answer)

    print(f"\n{'=' * 60}")
    print("✅ Day 1 完成！")
    print("   RAG 管线跑通：文档分块 -> 向量化灌入 Chroma -> 检索 top-k -> LLM 基于片段回答")
    print("   下一步 -> Day 2：混合检索（BM25+向量 RRF）+ Cross-Encoder 重排序")


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    print("🚀 第二周 Day 1：RAG 基础层（Embedding + 分块 + Chroma 向量库）\n")

    available = [p for p in PROVIDERS if p.get("enabled") and _is_real_key(p["api_key"])]
    if not available:
        print("❌ 没有可用的 provider！请检查 .env 配置")
        sys.exit(1)
    print(f"可用 provider: {', '.join(p['name'] for p in available)}")
    print(f"向量库: Chroma（持久化于 {DB_DIR.name}/）")
    print(f"Embedding: Chroma 默认 all-MiniLM-L6-v2（升级 bge-small-zh 见源码注释）\n")

    try:
        demo()
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
