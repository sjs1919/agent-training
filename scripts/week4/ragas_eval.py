"""
[AI:Claude] Week4 · RAGAS 评估（手写实现 4 指标）
================================================
评估 week2 混合检索 RAG 在合同问答上的表现。

设计取舍：
- 不依赖 ragas 库（ragas 库版本/依赖常出问题，且对 Provider 适配差）。
- 4 个指标（faithfulness / answer_relevancy / context_precision / context_recall）
  均按 RAGAS 方法论手写实现，用 week2 的 call_with_fallback 做 LLM-as-Judge。
- Ground Truth 来自 week2/data/contracts 的 3 份合同 + 历史延期记录，条款有精确数字。

复用 week2：
- call_with_fallback  -> LLM 裁判调用
- get_or_build_vectorstore / build_bm25_index / load_reranker -> 建库
- rag_answer_hybrid -> 待评估的 RAG 管线（拿 answer + hits）

阅读导航：docs/week4/补缺_week2_RAG.md 第 5 节（RAGAS 理论）。
"""

import json
import re
import sys
from pathlib import Path

# 引入 week2（与 day2 引入 day1 同样的套路）
WEEK2_DIR = Path(__file__).resolve().parent.parent / "week2"
sys.path.insert(0, str(WEEK2_DIR))

from day1_rag_basics import call_with_fallback, get_or_build_vectorstore  # noqa: E402
from day2_hybrid_rerank import (  # noqa: E402
    build_bm25_index,
    load_reranker,
    rag_answer_hybrid,
)


# ============================================================
# Ground Truth：5 个 Q&A 对，答案精确到条款数字
# 数据来源：scripts/week2/data/contracts/*.txt + 历史延期记录.txt
# ============================================================
GROUND_TRUTH = [
    {
        "id": "Q1",
        "question": "深圳精密五金合同中，逾期赔付比例是多少？累计逾期多少天可以解约？",
        "answer": (
            "逾期按订单金额的0.5%/日赔付；累计逾期超过5个工作日，客户可解除合同。"
        ),
    },
    {
        "id": "Q2",
        "question": "广州航天精工对不合格件如何处理？",
        "answer": (
            "实行100%全检（不抽检），不合格件直接报废，不得返工或让步接收，"
            "报废费用由供方承担。"
        ),
    },
    {
        "id": "Q3",
        "question": "东莞模具厂的大批量订单有什么折扣？",
        "answer": (
            "单批次500件以上享95折，1000件以上享9折，折扣不与加急费叠加。"
        ),
    },
    {
        "id": "Q4",
        "question": "广州航天精工的加工精度要求是什么？",
        "answer": (
            "采用五轴CNC加工，尺寸公差±0.01mm，致密度≥99.5%。"
        ),
    },
    {
        "id": "Q5",
        "question": "历史延期记录中，广州航天精工那次延期总共赔付了多少？",
        "answer": (
            "报废件费用36000元由供方承担，另按1%/日赔付订单金额2%共15000元，合计51000元。"
        ),
    },
]


# ============================================================
# LLM 裁判辅助
# ============================================================
def llm_text(system_prompt, user_prompt, max_tokens=800, temperature=0.0):
    """调 LLM 返回纯文本。temperature=0 让裁判结果稳定可复现。"""
    resp, _used, _log = call_with_fallback(
        system_prompt, user_prompt, max_tokens=max_tokens, temperature=temperature
    )
    return resp.choices[0].message.content.strip()


def _extract_json(text):
    """从模型输出里抠 JSON（兼容 ```json 代码块和裸 JSON）。"""
    # 先试代码块
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    payload = m.group(1).strip() if m else text.strip()
    return json.loads(payload)


def llm_json(system_prompt, user_prompt, max_tokens=800):
    """调 LLM 返回解析后的 JSON 对象。解析失败重试一次（追加"只输出JSON"指令）。"""
    for attempt in range(2):
        try:
            text = llm_text(system_prompt, user_prompt, max_tokens=max_tokens)
            return _extract_json(text)
        except (json.JSONDecodeError, ValueError) as e:
            if attempt == 0:
                # 重试时更强约束
                user_prompt = user_prompt + "\n\n（请只输出合法 JSON，不要任何解释文字）"
            else:
                raise RuntimeError(f"LLM 返回非合法 JSON: {e}\n原始输出:\n{text}")


# ============================================================
# 指标 1：faithfulness（C -> A，答案是否忠于检索内容）
# 公式：能被 Context 支持的原子陈述数 / 总陈述数
# ============================================================
def faithfulness(answer, contexts):
    if not answer.strip():
        return 0.0, {"statements": [], "supported": 0, "total": 0}

    context_text = "\n---\n".join(
        f"[片段{i}] {c['text']}" for i, c in enumerate(contexts, 1)
    ) if contexts else "（无检索内容）"

    # 步骤1：把 answer 拆成原子陈述
    stmts = llm_json(
        system_prompt=(
            "你是事实抽取助手。把给定回答拆成【原子事实陈述】（每条只含一个事实）。"
            "输出 JSON：{\"statements\": [\"陈述1\", \"陈述2\", ...]}。"
            "不要合并多条事实到一句。"
        ),
        user_prompt=f"回答：\n{answer}",
    )
    statements = stmts.get("statements", [])
    if not statements:
        return 0.0, {"statements": [], "supported": 0, "total": 0}

    # 步骤2：批量判断每条陈述是否被 context 支持
    judge = llm_json(
        system_prompt=(
            "你是事实核查员。对每条【陈述】，判断它能否从【检索内容】直接推出或被支持。\n"
            "判定规则：\n"
            "- 能从检索内容推出 -> supported=true\n"
            "- 检索内容未提及 / 与检索内容矛盾 / 需要外部知识 -> supported=false\n"
            "输出 JSON：{\"results\": [{\"statement\": \"...\", \"supported\": true/false}]}。"
        ),
        user_prompt=(
            f"检索内容：\n{context_text}\n\n"
            f"待核查陈述：\n{json.dumps(statements, ensure_ascii=False)}"
        ),
    )
    results = judge.get("results", [])
    supported = sum(1 for r in results if r.get("supported"))
    total = len(statements)
    score = supported / total if total else 0.0
    return score, {
        "statements": statements,
        "results": results,
        "supported": supported,
        "total": total,
    }


# ============================================================
# 指标 2：answer_relevancy（Q -> A，回答是否切题）
# RAGAS 方法：让 LLM 由 Answer 反推问题，再看反推问题与原问题是否语义一致。
# 简化点：用 LLM 判定语义一致（yes/no）代替 embedding 余弦相似度。
# ============================================================
def answer_relevancy(question, answer, n_reverse=2):
    if not answer.strip():
        return 0.0, {"reverse_questions": [], "matches": 0}

    # 步骤1：由 answer 反推 n 个可能的问题
    rq = llm_json(
        system_prompt=(
            "根据给定【回答】，反推它可能在回答什么问题。"
            f"生成 {n_reverse} 个不同角度的问题。"
            "输出 JSON：{\"questions\": [\"问题1\", \"问题2\"]}。"
            "问题应只基于回答内容，不要引入回答外的信息。"
        ),
        user_prompt=f"回答：\n{answer}",
    )
    reverse_qs = rq.get("questions", [])[:n_reverse]
    if not reverse_qs:
        return 0.0, {"reverse_questions": [], "matches": 0}

    # 步骤2：判定每个反推问题与原问题的语义一致性
    judge = llm_json(
        system_prompt=(
            "判断【反推问题】与【原问题】是否在问【同一主题】。\n"
            "判定规则（宽松匹配，抓核心意图）：\n"
            "- 只要两个问题关心的主体/主题一致，就算 match=true，不必字面相同、不必范围完全一致\n"
            "- 反推问题比原问题多带细节（如多了文件名、多了子问）不算否定理由，看主干\n"
            "- 仅当反推问题明显在问另一件事（主题偏移）才 match=false\n"
            "举例：原'广州航天不合格件怎么处理' vs 反推'广州航天全检不合格件供方怎么处理' -> match=true\n"
            "输出 JSON：{\"results\": [{\"reverse\": \"...\", \"match\": true/false}]}。"
        ),
        user_prompt=(
            f"原问题：{question}\n\n"
            f"反推问题列表：\n{json.dumps(reverse_qs, ensure_ascii=False)}"
        ),
    )
    results = judge.get("results", [])
    matches = sum(1 for r in results if r.get("match"))
    score = matches / len(reverse_qs) if reverse_qs else 0.0
    return score, {
        "reverse_questions": reverse_qs,
        "results": results,
        "matches": matches,
        "total": len(reverse_qs),
    }


# ============================================================
# 指标 3：context_precision（C vs G，相关文档是否排在前面）
# 公式（Average Precision）：对 top-k 中每个相关位次 i，
#   precision@i = (前 i 个中相关数) / i
#   score = sum(precision@i for 相关 i) / 相关总数；无相关则 0
# ============================================================
def context_precision(contexts, ground_truth):
    if not contexts:
        return 0.0, {"relevance": [], "relevant_count": 0}

    # 逐个判断每个片段对答出 ground_truth 是否有用
    judge = llm_json(
        system_prompt=(
            "判断每个【检索片段】对回答【标准答案】是否有用（含答案所需的关键事实）。"
            "输出 JSON：{\"results\": [{\"index\": 1, \"relevant\": true/false}]}。"
            "index 从 1 开始，按输入顺序。"
        ),
        user_prompt=(
            f"标准答案：\n{ground_truth}\n\n"
            f"检索片段：\n"
            + "\n".join(f"[{i}] {c['text']}" for i, c in enumerate(contexts, 1))
        ),
    )
    results = judge.get("results", [])
    # 对齐：按 index 取 relevant，缺失视为 false
    rel_flags = []
    for i in range(1, len(contexts) + 1):
        r = next((x for x in results if x.get("index") == i), None)
        rel_flags.append(bool(r.get("relevant")) if r else False)

    relevant_count = sum(rel_flags)
    if relevant_count == 0:
        return 0.0, {"relevance": rel_flags, "relevant_count": 0}

    # 计算 Average Precision
    cum_relevant = 0
    ap_sum = 0.0
    for i, rel in enumerate(rel_flags, 1):
        if rel:
            cum_relevant += 1
            ap_sum += cum_relevant / i  # precision@i
    score = ap_sum / relevant_count
    return score, {
        "relevance": rel_flags,
        "relevant_count": relevant_count,
        "total": len(contexts),
    }


# ============================================================
# 指标 4：context_recall（G -> C，标准答案的信息是否被检索到）
# 公式：能从 Context 找到的 ground_truth 原子陈述数 / 总陈述数
# ============================================================
def context_recall(ground_truth, contexts):
    context_text = "\n---\n".join(
        f"[片段{i}] {c['text']}" for i, c in enumerate(contexts, 1)
    ) if contexts else "（无检索内容）"

    # 步骤1：拆 ground truth 成原子陈述
    stmts = llm_json(
        system_prompt=(
            "你是事实抽取助手。把给定【标准答案】拆成【原子事实陈述】。"
            "输出 JSON：{\"statements\": [\"陈述1\", ...]}。"
        ),
        user_prompt=f"标准答案：\n{ground_truth}",
    )
    statements = stmts.get("statements", [])
    if not statements:
        return 0.0, {"statements": [], "found": 0, "total": 0}

    # 步骤2：判断每条是否能在 context 找到
    judge = llm_json(
        system_prompt=(
            "你是事实核查员。对每条【陈述】，判断它是否能从【检索内容】中找到对应信息。\n"
            "- 检索内容含该信息（即使措辞不同）-> found=true\n"
            "- 检索内容未含 -> found=false\n"
            "输出 JSON：{\"results\": [{\"statement\": \"...\", \"found\": true/false}]}。"
        ),
        user_prompt=(
            f"检索内容：\n{context_text}\n\n"
            f"待核查陈述：\n{json.dumps(statements, ensure_ascii=False)}"
        ),
    )
    results = judge.get("results", [])
    found = sum(1 for r in results if r.get("found"))
    total = len(statements)
    score = found / total if total else 0.0
    return score, {
        "statements": statements,
        "results": results,
        "found": found,
        "total": total,
    }


# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 70)
    print("RAGAS 评估：评估 week2 混合检索 RAG（4 指标，LLM-as-Judge）")
    print("=" * 70)

    # 1. 建 week2 检索管线
    print("\n📦 初始化 week2 检索管线（向量库 + BM25 + Reranker）...")
    collection = get_or_build_vectorstore()
    bm25, chunks, metas = build_bm25_index(collection)
    reranker = load_reranker()

    # 2. 逐题评估
    rows = []
    agg = {"faithfulness": [], "answer_relevancy": [],
           "context_precision": [], "context_recall": []}

    for gt in GROUND_TRUTH:
        q = gt["question"]
        print(f"\n{'─' * 70}")
        print(f"【{gt['id']}】{q}")

        # 跑 week2 RAG 拿 answer + 检索片段
        answer, hits, _used = rag_answer_hybrid(
            collection, bm25, chunks, metas, reranker, q, top_k=3, verbose=False
        )
        print(f"  生成回答：{answer}")
        print(f"  检索命中 {len(hits)} 片段")

        # 4 指标
        f_score, f_detail = faithfulness(answer, hits)
        ar_score, ar_detail = answer_relevancy(q, answer)
        cp_score, cp_detail = context_precision(hits, gt["answer"])
        cr_score, cr_detail = context_recall(gt["answer"], hits)

        agg["faithfulness"].append(f_score)
        agg["answer_relevancy"].append(ar_score)
        agg["context_precision"].append(cp_score)
        agg["context_recall"].append(cr_score)

        rows.append({
            "id": gt["id"],
            "faithfulness": f_score,
            "answer_relevancy": ar_score,
            "context_precision": cp_score,
            "context_recall": cr_score,
            "detail": {
                "faithfulness": f_detail,
                "answer_relevancy": ar_detail,
                "context_precision": cp_detail,
                "context_recall": cr_detail,
            },
        })
        print(f"  faithfulness={f_score:.2f}  answer_relevancy={ar_score:.2f}  "
              f"context_precision={cp_score:.2f}  context_recall={cr_score:.2f}")

    # 3. 汇总报告
    print("\n" + "=" * 70)
    print("评估汇总")
    print("=" * 70)
    header = f"{'题号':<6}{'faithfulness':<16}{'answer_relevancy':<20}{'context_precision':<20}{'context_recall':<16}"
    print(header)
    print("-" * 70)
    for r in rows:
        print(f"{r['id']:<6}{r['faithfulness']:<16.2f}{r['answer_relevancy']:<20.2f}"
              f"{r['context_precision']:<20.2f}{r['context_recall']:<16.2f}")
    print("-" * 70)
    print(f"{'平均':<6}"
          f"{sum(agg['faithfulness'])/len(rows):<16.2f}"
          f"{sum(agg['answer_relevancy'])/len(rows):<20.2f}"
          f"{sum(agg['context_precision'])/len(rows):<20.2f}"
          f"{sum(agg['context_recall'])/len(rows):<16.2f}")

    # 4. 写明细到 tmp（不提交 Git）
    tmp_dir = Path(__file__).resolve().parents[2] / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    out = tmp_dir / "ragas_eval_result.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"\n💾 明细已写入：{out}")

    # 5. 简要解读
    print("\n📖 解读：")
    print("  - faithfulness 低 -> 模型在编造（检索没有却说了）-> 加 Rubric-checked 拦截")
    print("  - context_recall 低 -> 检索没召回标准答案所需信息 -> 调分块/换 embedding/加 BM25")
    print("  - context_precision 低 -> 相关片段没排前面 -> 检查重排")
    print("  - answer_relevancy 低 -> 回答跑题 -> 检查 prompt/temperature")
    print("  配套：scripts/week4/rubric_checked_rag.py 用 Rubric 提升 faithfulness。")


if __name__ == "__main__":
    main()
