"""
第二周 · Day 2 - RAG 基础层进阶（混合检索 + 重排序）
======================================================
目标：治 Day1 纯向量检索的中文召回弱问题。
      Day1 用 Chroma 默认 MiniLM，top1 常召回"历史延期记录"而非目标合同。
      Day2 加 BM25（关键词精确）+ RRF 融合 + Cross-Encoder 重排，把目标合同顶到 top1。

核心认知：
  - 向量检索：语义相似（"延期赔付"≈"违约金"），但中文弱模型召回偏；
  - BM25：关键词精确匹配（"广州航天"必须字面命中），补向量短板；
  - RRF：两路排名融合，兼顾语义 + 关键词；
  - Reranker：Cross-Encoder 对 (query, chunk) 精排，最终 top1 最相关。

知识块：⑤ RAG 检索增强
今日栈：jieba（中文分词）+ rank_bm25 + sentence-transformers（Cross-Encoder）+ 复用 Day1 Chroma
业务域：3D 打印/CNC 调度（合同条款 + 历史延期记录）

[AI:Claude] 架构设计：混合检索（向量 + BM25 RRF）+ Cross-Encoder 重排，复用 Day1 向量库
"""

import os
import sys
from pathlib import Path

# ---- 复用 day1 的 Provider + 向量库 ----
sys.path.insert(0, str(Path(__file__).parent))
from day1_rag_basics import (  # noqa: E402
    PROVIDERS,
    call_with_fallback,
    _is_real_key,
    get_or_build_vectorstore,
    retrieve,
    RAG_SYSTEM_PROMPT,
)

import jieba  # noqa: E402
from rank_bm25 import BM25Okapi  # noqa: E402
from sentence_transformers import CrossEncoder  # noqa: E402

# Windows stdout UTF-8（开箱即跑）
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


# ============================================================
# 第一部分：BM25 索引（中文 jieba 分词）
# 导航：阅读导航_week1_week2.md → Week2 周二 → "BM25 关键词检索原理"
# 知识：BM25 是关键词精确匹配，补向量检索的短板
#       公式：IDF × TF / (TF + k × (1-b + b × doc_len/avg_len))
#       擅长：订单号、客户名、产品名等精确命中
#       向量检索擅长"语义相似"（加急≈紧急），BM25 擅长"字面匹配"（广州航天必须含"广州"）
# ============================================================

def build_bm25_index(collection):
    """
    从 Chroma 向量库取出全部 chunk，jieba 分词后建 BM25 索引。
    返回 (bm25, chunks, metas)，供 bm25_search 用。

    【原子操作】BM25 索引构建三步骤：
    ① collection.get() → 取出所有已存储的 chunk（复用 Day1 灌入的数据）
    ② jieba.cut(chunk) → 中文分词（BM25 需要 token 列表，不是原始文本）
    ③ BM25Okapi(tokenized) → 构建 BM25 索引（每个文档的 term frequency 矩阵）
    """
    data = collection.get(include=["documents", "metadatas"])
    chunks = data["documents"]
    metas = data["metadatas"]
    # jieba 精确模式分词；BM25 需要 token 列表
    tokenized = [list(jieba.cut(c)) for c in chunks]
    bm25 = BM25Okapi(tokenized)
    print(f"  📚 BM25 索引建好：{len(chunks)} 个 chunk")
    return bm25, chunks, metas


def bm25_search(bm25, chunks, metas, query, top_k=10):
    """
    BM25 检索：query 分词 -> 算各 chunk 分数 -> 取 top_k。
    返回 [{text, source, score, rank}]，rank 从 1 开始（供 RRF 用）。
    """
    query_tokens = list(jieba.cut(query))
    scores = bm25.get_scores(query_tokens)
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    hits = []
    for idx, score in ranked[:top_k]:
        if score <= 0:
            continue  # BM25 零分（无关键词命中）跳过
        hits.append({
            "text": chunks[idx],
            "source": metas[idx].get("source", "?"),
            "score": float(score),
            "rank": len(hits) + 1,
        })
    return hits


# ============================================================
# 第二部分：RRF 融合（Reciprocal Rank Fusion）
# 导航：阅读导航_week1_week2.md → Week2 周二 → "RRF 融合"
# 知识：两路检索（向量+BM25）各自排序 → RRF 合并排名
#       公式：RRF(d) = Σ 1/(k + rank_i(d))，k 一般取 60
#       如果一个 chunk 在两路都命中，RRF 分数累加 → 排更靠前
#       本质：不关心分数绝对值，只关心排名位置
# ============================================================

def rrf_fuse(vector_hits, bm25_hits, k=60, top_k=10):
    """
    RRF 融合：两路检索结果按排名融合。

    【原子操作】RRF 融合：
    ① 两路结果各自按 rank 打分：1/(k + rank)，rank 从 1（最相关）开始
    ② 相同 chunk 的分数累加（两路都命中 → 分数更高）
    ③ 按累加分数降序取 top_k
    为什么用 RRF 而不是线性加权？因为我们不需要调权重参数——
    RRF 只看"排名位置"，对分数尺度不敏感（向量 distance 0~2，BM25 score 0~N）
    详见：阅读导航 → Week2 周二 → "RRF 融合"
    """
    scores = {}  # key: chunk text -> rrf score
    info = {}    # key: chunk text -> {text, source}
    for h in vector_hits:
        key = h["text"]
        rank = h.get("rank", 1)
        scores[key] = scores.get(key, 0) + 1.0 / (k + rank)
        info[key] = {"text": h["text"], "source": h["source"]}
    for h in bm25_hits:
        key = h["text"]
        rank = h.get("rank", 1)
        scores[key] = scores.get(key, 0) + 1.0 / (k + rank)
        info[key] = {"text": h["text"], "source": h["source"]}
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    result = []
    for key, score in ranked[:top_k]:
        item = dict(info[key])
        item["rrf_score"] = score
        result.append(item)
    return result


# ============================================================
# 第三部分：Cross-Encoder 重排
# 导航：阅读导航_week1_week2.md → Week2 周二 → "Cross-Encoder 重排序"
# 知识：Cross-Encoder vs 双塔(向量Embedding) 的区别：
#       双塔：query 和 doc 各自编码成独立向量 → 余弦距离比远近（快，~100ms/千篇）
#       Cross-Encoder：query+doc 拼接后一起推理 → 输出 0-1 相关分数（慢，~100ms/对）
#       Cross-Encoder 更准因为能看到 query 和 doc 的交互，双塔只看各自向量方向
#       生产流程：向量(快)召回 top-20 → Cross-Encoder(准)重排取 top-3
# ============================================================

RERANKER_MODEL = "BAAI/bge-reranker-base"
_PROXY = os.environ.get("HTTPS_PROXY", os.environ.get("HTTP_PROXY", "http://127.0.0.1:7890"))


def load_reranker(model_name=RERANKER_MODEL):
    """
    加载 Cross-Encoder reranker。
    优先离线加载（模型已缓存时跳过 HF 联网检查，避免代理 SSL EOF）；
    未缓存则走 Clash 代理 3450 从 HF 下载（~1.1GB），之后秒载。
    LLM 调用用 trust_env=False 直连，不受此代理影响。
    """
    print(f"  ⏬ 加载 reranker（{model_name}）...")
    # 优先离线：已缓存则不联网，跳过 HF HEAD 检查（避免代理 SSL EOF）
    # HF_HUB_OFFLINE 管 huggingface_hub，TRANSFORMERS_OFFLINE 管 transformers，
    # 两者都设才彻底阻止 modules.json/adapter_config.json 等 HEAD 检查
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    # huggingface_hub 在 import 时把 HF_HUB_OFFLINE 固化到 constants，
    # 运行时设 os.environ 无效，必须直接 patch constants 才能跳过 HEAD 检查
    # （否则每个 modules.json/adapter_config.json 等 HEAD 要等 Windows TCP 超时 ~21s ×5 retry）
    try:
        import huggingface_hub.constants as _hf_const
        _hf_const.HF_HUB_OFFLINE = True
    except Exception:
        pass
    try:
        model = CrossEncoder(model_name)
        print(f"  ✅ reranker 就绪（离线缓存）")
        return model
    except Exception as offline_err:
        # 离线失败（模型未缓存）-> 走代理下载
        os.environ.pop("HF_HUB_OFFLINE", None)
        os.environ.pop("TRANSFORMERS_OFFLINE", None)
        try:
            import huggingface_hub.constants as _hf_const
            _hf_const.HF_HUB_OFFLINE = False
        except Exception:
            pass
        os.environ["HTTPS_PROXY"] = _PROXY
        os.environ["HTTP_PROXY"] = _PROXY
        try:
            model = CrossEncoder(model_name)
        except Exception as e:
            raise RuntimeError(
                f"reranker 加载失败（离线: {offline_err}; 代理: {e}）\n"
                f"可能原因：① 模型未缓存且 Clash 代理未开（3450）；② 网络不通。"
            )
        finally:
            os.environ.pop("HTTPS_PROXY", None)
            os.environ.pop("HTTP_PROXY", None)
        print(f"  ✅ reranker 就绪（走代理下载并缓存）")
        return model


def rerank(reranker, query, candidates, top_k=3):
    """
    Cross-Encoder 重排：对每个 (query, chunk) 对算相关分，按分排序取 top_k。
    返回 [{text, source, rrf_score, rerank_score}]。

    【原子操作】重排的输入输出：
    输入：(query, [chunk1, chunk2, ...]) → 每个 chunk 和 query 拼接成对
    处理：reranker.predict([[query, c1], [query, c2], ...]) → 每个 pair 一个 0-1 分数
    输出：按 rerank_score 降序取 top_k
    关键认知：RRF 已经做了第一次排序（用排名位置），
             Cross-Encoder 做第二次精确排序（用语义相关度）。
    """
    if not candidates:
        return []
    pairs = [[query, c["text"]] for c in candidates]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    result = []
    for c, score in ranked[:top_k]:
        item = dict(c)
        item["rerank_score"] = float(score)
        result.append(item)
    return result


# ============================================================
# 第四部分：混合检索主函数
# ============================================================

def _retrieve_hybrid_full(collection, bm25, chunks, metas, reranker, query, top_k=3):
    """
    混合检索全流程，返回 (final, vector_hits, bm25_hits)，供 demo 对比中间结果。
    """
    # 1. 向量检索（复用 day1 retrieve，取 10 候选）
    vector_hits = retrieve(collection, query, top_k=10)
    for i, h in enumerate(vector_hits, 1):
        h["rank"] = i
    # 2. BM25 检索
    bm25_hits = bm25_search(bm25, chunks, metas, query, top_k=10)
    # 3. RRF 融合
    fused = rrf_fuse(vector_hits, bm25_hits, k=60, top_k=10)
    # 4. Cross-Encoder 重排
    final = rerank(reranker, query, fused, top_k=top_k)
    return final, vector_hits, bm25_hits


def retrieve_hybrid(collection, bm25, chunks, metas, reranker, query, top_k=3):
    """
    [AI:Claude] 混合检索主函数，四步：
    1. 向量检索（复用 day1 retrieve，取 10 候选）
    2. BM25 检索（jieba 分词，取 10 候选）
    3. RRF 融合（两路排名合并，取 10）
    4. Cross-Encoder 重排（精排，取 top_k）

    返回 [{text, source, rrf_score, rerank_score}]，结构与 day1 retrieve 兼容
    （day1 返回 {text, source, distance}，本函数用 rerank_score 替代 distance）。
    """
    final, _, _ = _retrieve_hybrid_full(collection, bm25, chunks, metas, reranker, query, top_k=top_k)
    return final


# ============================================================
# 第五部分：端到端 RAG（用混合检索替代 day1 纯向量）
# ============================================================

def rag_answer_hybrid(collection, bm25, chunks, metas, reranker, query, top_k=3, verbose=True):
    """用 retrieve_hybrid 检索 + LLM 生成（对比 day1 的 rag_answer）"""
    if verbose:
        print(f"\n🔍 混合检索：{query}")
    hits = retrieve_hybrid(collection, bm25, chunks, metas, reranker, query, top_k=top_k)
    if verbose:
        print(f"  重排后 top {len(hits)}：")
        for i, h in enumerate(hits, 1):
            print(f"  [{i}] 来源:{h['source']}  rerank分:{h['rerank_score']:.4f}")

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
# 演示：对比 day1 纯向量 vs day2 混合 + 重排
# ============================================================

def demo():
    print("=" * 60)
    print("第一部分：加载向量库 + BM25 索引 + Reranker")
    print("=" * 60)
    collection = get_or_build_vectorstore()
    bm25, chunks, metas = build_bm25_index(collection)
    reranker = load_reranker()

    # day4 暴露的失败 case：day1 top1 常召回"历史延期记录"而非目标合同
    compare_queries = [
        "广州航天精工合同特殊条款",
        "深圳精密五金合同延期赔付条款",
        "加急订单的风险和合同特殊条款",
        "航天精密件的质检要求是什么",
    ]

    print(f"\n{'=' * 60}")
    print("第二部分：检索对比（day1 纯向量 vs day2 混合+重排）")
    print("=" * 60)
    print("  目标：day2 把目标合同顶到 top1（day1 top1 常是历史延期记录）")

    for q in compare_queries:
        print(f"\n{'─' * 60}")
        print(f"🔎 查询：{q}")

        # day1 纯向量
        v_hits = retrieve(collection, q, top_k=3)
        print(f"  [day1 纯向量 top3]")
        for i, h in enumerate(v_hits, 1):
            print(f"    {i}. {h['source']}  (距离 {h['distance']:.4f})")

        # day2 混合 + 重排
        h_hits, _, _ = _retrieve_hybrid_full(collection, bm25, chunks, metas, reranker, q, top_k=3)
        print(f"  [day2 混合+重排 top3]")
        for i, h in enumerate(h_hits, 1):
            print(f"    {i}. {h['source']}  (rerank分 {h['rerank_score']:.4f})")

        # 判定 top1 是否改进
        v_top1 = v_hits[0]["source"] if v_hits else "无"
        h_top1 = h_hits[0]["source"] if h_hits else "无"
        improved = "历史延期记录" in v_top1 and "历史延期记录" not in h_top1
        flag = "✅ 改进" if improved else ("⬜ 持平" if v_top1 == h_top1 else "⚠️ 变化")
        print(f"  -> top1: {v_top1} ➜ {h_top1}  {flag}")

    print(f"\n{'=' * 60}")
    print("第三部分：端到端 RAG（混合检索 + LLM 生成）")
    print("=" * 60)
    rag_q = "广州航天精工的合同有什么特殊要求？质检不合格怎么办？"
    print(f"  问题：{rag_q}")
    answer, hits, used = rag_answer_hybrid(collection, bm25, chunks, metas, reranker, rag_q)
    print(f"\n💬 回答（provider: {used['name']}）：")
    print(answer)

    print(f"\n{'=' * 60}")
    print("✅ Day 2 完成！")
    print("   混合检索（向量 + BM25 RRF）+ Cross-Encoder 重排跑通")
    print("   对比 day1：纯向量中文召回弱，day2 关键词 + 语义 + 精排三路兼顾")
    print("   下一步 -> 顺手改 day4 的 search_knowledge_base 用 retrieve_hybrid")


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    print("🚀 第二周 Day 2：混合检索 + 重排序（BM25 + RRF + Cross-Encoder）\n")

    available = [p for p in PROVIDERS if p.get("enabled") and _is_real_key(p["api_key"])]
    if not available:
        print("❌ 没有可用的 provider！请检查 .env 配置")
        sys.exit(1)
    print(f"可用 provider: {', '.join(p['name'] for p in available)}")
    print(f"检索: 向量(Chroma MiniLM) + BM25(jieba) + RRF融合 + Cross-Encoder({RERANKER_MODEL})")
    print(f"首次加载 reranker 走 Clash 代理 {_PROXY}（已缓存则秒载）\n")

    try:
        demo()
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
