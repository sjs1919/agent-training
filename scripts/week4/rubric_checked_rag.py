"""
[AI:Claude] Week4 · Agentic RAG 模式②：Rubric-checked（Evaluator-optimizer）
============================================================================
对应 docs/week4/补缺_week2_RAG.md 第 6 节选型表里的 ② 号模式。

机制：
    query -> 检索 -> 生成答案 -> [Grader 按 Rubric 打分]
                                  ├─ 全过 -> 返回答案
                                  └─ 有失败 -> 反馈给生成器 -> 重生成（循环）
    最多 max_iter 次，仍未通过则返回最后一次答案并标注未达标。

为什么合同场景需要它：
    合同条款涉及钱和解约权，漏一条或编一个数字就出事。
    Rubric 把"不能漏、不能编"变成可检查的规则，用第二个 LLM（grader）兜底。
    这是 week2 线性 RAG 没有的"后验拦截"层（见补缺_week2_RAG.md 第 8 节第 4 层）。

复用 week2：
    retrieve_hybrid -> 混合检索（向量+BM25+RRF+重排）
    call_with_fallback -> 生成器与 grader 共用 LLM
    RAG_SYSTEM_PROMPT -> 复用 week2 的系统提示

阅读导航：docs/week4/补缺_week2_RAG.md 第 6.3 节②。
"""

import json
import sys
from pathlib import Path

# 引入 week2 检索能力
WEEK2_DIR = Path(__file__).resolve().parent.parent / "week2"
sys.path.insert(0, str(WEEK2_DIR))

# 引入同周次的 LLM 裁判辅助（llm_text / llm_json 定义在 ragas_eval.py）
WEEK4_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(WEEK4_DIR))

from day1_rag_basics import RAG_SYSTEM_PROMPT, call_with_fallback  # noqa: E402
from day2_hybrid_rerank import (  # noqa: E402
    build_bm25_index,
    get_or_build_vectorstore,
    load_reranker,
    retrieve_hybrid,
)
from ragas_eval import llm_json, llm_text  # noqa: E402


# ============================================================
# Rubric：合同问答的评分细则
# 每条规则可被 grader 独立判定 pass/fail，失败时给生成器具体反馈。
# ============================================================
RUBRIC = [
    {
        "id": "grounded",
        "rule": "回答中每个具体数字、费率、天数、金额都必须能在检索片段中找到出处，不得编造。",
    },
    {
        "id": "complete",
        "rule": "针对用户问题问到的每个点，检索片段里有的关键条款都必须覆盖，不得遗漏。",
    },
    {
        "id": "no_external",
        "rule": "回答不得使用检索片段以外的知识补充具体事实（常识性连接词除外）。",
    },
    {
        "id": "cited",
        "rule": "回答应标注关键信息的来源（合同号或文件名）。",
    },
]


# ============================================================
# 生成器：首答 / 根据反馈修订
# ============================================================
GENERATE_SYSTEM = (
    RAG_SYSTEM_PROMPT
    + "\n\n额外要求：回答时标注关键信息的来源（如【深圳精密五金合同】）。"
    "若检索片段不足以回答，直接说明'未在合同中找到相关条款'，不要编造。"
)


def generate(query, context_text, prev_answer=None, feedback=None):
    """
    首答：prev_answer=None。
    修订：传入 prev_answer + feedback，让模型在原答案基础上按反馈改。
    """
    if prev_answer is None:
        user = f"检索片段：\n{context_text}\n\n用户问题：{query}"
    else:
        user = (
            f"检索片段：\n{context_text}\n\n用户问题：{query}\n\n"
            f"你上一版的回答：\n{prev_answer}\n\n"
            f"评分员反馈（请针对性修订）：\n{feedback}\n\n"
            "请输出修订后的回答。"
        )
    resp, _used, _log = call_with_fallback(
        GENERATE_SYSTEM, user, max_tokens=500, temperature=0.2
    )
    return resp.choices[0].message.content.strip()


# ============================================================
# Grader：按 Rubric 逐条检查
# ============================================================
def grade(query, answer, contexts):
    """返回 (passed: bool, checks: list, feedback: str)。"""
    context_text = "\n---\n".join(
        f"[片段{i}] {c['text']}" for i, c in enumerate(contexts, 1)
    ) if contexts else "（无检索内容）"

    rubric_text = "\n".join(
        f"({i}) [{r['id']}] {r['rule']}" for i, r in enumerate(RUBRIC, 1)
    )

    result = llm_json(
        system_prompt=(
            "你是合同问答的评分员。按下方【评分细则】逐条检查【回答】。\n"
            "判定规则：\n"
            "- 回答满足该条 -> passed=true\n"
            "- 回答违反或不满足 -> passed=false，并在 reason 写明具体哪里不达标\n"
            "输出 JSON：\n"
            "{\"checks\": [{\"id\": \"grounded\", \"passed\": true, \"reason\": \"...\"}, ...], "
            "\"passed\": true/false, \"feedback\": \"若未通过，给生成器的具体修订建议；若通过则为空\"}。"
            "checks 必须覆盖所有细则条目。passed 为所有条目均 passed 时才为 true。"
        ),
        user_prompt=(
            f"用户问题：{query}\n\n"
            f"检索片段：\n{context_text}\n\n"
            f"回答：\n{answer}\n\n"
            f"评分细则：\n{rubric_text}"
        ),
    )

    checks = result.get("checks", [])
    passed = bool(result.get("passed", False))
    feedback = result.get("feedback", "") or ""
    # 兜底：若模型没填 passed，按 checks 自行聚合
    if not checks:
        passed = False
    elif not result.get("passed"):
        passed = all(c.get("passed") for c in checks)

    if not passed and not feedback:
        feedback = "；".join(
            f"[{c.get('id')}] {c.get('reason', '不达标')}"
            for c in checks if not c.get("passed")
        )
    return passed, checks, feedback


# ============================================================
# 主循环：Rubric-checked RAG
# ============================================================
def rubric_checked_rag(query, max_iter=3, verbose=True):
    """
    query -> 检索 -> 生成 -> 评分 -> (不达标则修订循环)。
    返回 {answer, hits, iterations, passed, checks}。
    """
    # 0. 建检索资源（外部已建好可传入；这里 demo 自建）
    collection = get_or_build_vectorstore()
    bm25, chunks, metas = build_bm25_index(collection)
    reranker = load_reranker()

    # 1. 检索
    hits = retrieve_hybrid(collection, bm25, chunks, metas, reranker, query, top_k=3)
    context_text = "\n\n".join(
        f"【片段{i}】(来源:{h['source']})\n{h['text']}"
        for i, h in enumerate(hits, 1)
    )
    if verbose:
        print(f"  🔍 检索命中 {len(hits)} 片段")

    # 2. 生成 -> 评分 -> 修订循环
    answer = generate(query, context_text)
    history = []
    passed = False
    checks = []
    it = 0

    for it in range(1, max_iter + 1):
        passed, checks, feedback = grade(query, answer, hits)
        history.append({"iteration": it, "answer": answer, "checks": checks, "passed": passed})
        if verbose:
            fails = [c["id"] for c in checks if not c.get("passed")]
            print(f"  📋 第 {it} 轮评分：{'通过' if passed else '未通过' + str(fails)}")

        if passed:
            break
        if it >= max_iter:
            if verbose:
                print(f"  ⚠️ 达到最大轮次 {max_iter}，仍未通过，返回最后版本")
            break

        # 修订
        if verbose:
            print(f"  🔧 按反馈修订：{feedback[:80]}...")
        answer = generate(query, context_text, prev_answer=answer, feedback=feedback)

    return {
        "answer": answer,
        "hits": hits,
        "iterations": it,
        "passed": passed,
        "checks": checks,
        "history": history,
    }


# ============================================================
# Demo：对比 week2 纯 RAG vs Rubric-checked RAG
# ============================================================
DEMO_QUERIES = [
    "深圳精密五金合同逾期 8 天会怎样？订单金额 20 万。",
    "广州航天精工的不合格件怎么处理？逾期赔付比例是多少？",
    "东莞模具厂下 800 件订单有什么优惠？逾期怎么算？",
]


def demo():
    print("=" * 70)
    print("Rubric-checked RAG（Agentic RAG 模式②：Evaluator-optimizer）")
    print("=" * 70)
    print("对比：week2 线性 RAG（一次生成）vs Rubric-checked（生成+评分+修订循环）")
    print("Rubric 细则：")
    for r in RUBRIC:
        print(f"  - [{r['id']}] {r['rule']}")

    # 用 week2 纯 RAG 做基线对比
    from day2_hybrid_rerank import rag_answer_hybrid

    collection = get_or_build_vectorstore()
    bm25, chunks, metas = build_bm25_index(collection)
    reranker = load_reranker()

    for q in DEMO_QUERIES:
        print(f"\n{'─' * 70}")
        print(f"❓ {q}")

        # 基线：week2 一次生成
        baseline, _hits, _ = rag_answer_hybrid(
            collection, bm25, chunks, metas, reranker, q, top_k=3, verbose=False
        )
        print(f"\n[week2 基线] {baseline}")

        # Rubric-checked
        print(f"\n[Rubric-checked]")
        result = rubric_checked_rag(q, max_iter=3, verbose=True)
        print(f"  ✅ 最终答案（第 {result['iterations']} 轮，"
              f"{'通过' if result['passed'] else '未通过'}）：")
        print(f"  {result['answer']}")

    # 明细落 tmp
    tmp_dir = Path(__file__).resolve().parents[2] / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    print(f"\n💡 说明：Rubric-checked 用第二个 LLM 当评分员，对合同场景的"
          f"'漏条款''编数字'做后验拦截。代价是每题多 1~3 次 LLM 调用。")
    print(f"   评估这个拦截效果，用 scripts/week4/ragas_eval.py 看 faithfulness 是否提升。")


if __name__ == "__main__":
    demo()
