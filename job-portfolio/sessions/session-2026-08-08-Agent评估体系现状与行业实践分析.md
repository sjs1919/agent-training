# Session: Agent 评估体系现状梳理 + 行业实践分析

> 日期：2026-08-08
> 话题：demo 评估体系现状核查 → ragas 停滞确认 → 行业最佳实践调研 → 落盘分析文档
> 状态：分析已落盘，改造方向待定

---

## 本次完成

### 1. 核查 demo 当前评估体系

读 `demo/eval/` 三个文件，确认现状：
- `ground_truth.json`：10 个排产场景（expected_tools / expected_order_ids / checks）
- `metrics.py`：手写 3 指标（工具F1×0.3 + 完整性×0.5 + 订单召回×0.2）
- `runner.py`：遍历 10 case，case ≥0.6 算 pass，回归基线 ≥7/10

**硬伤**：
- `min_tools_called` 字段 metrics.py 根本没读
- 完整性检查是子串匹配（`must_contain`），语义不对也判过
- 缺 LLM-as-Judge 语义指标
- context 没被采集（`search_knowledge_base` 把 hits 展平成字符串）
- 缺 trajectory 评估（只看工具名，不看参数/顺序/重试）

### 2. 确认 ragas 停滞事实

- pip index 显示 **0.4.3 就是 PyPI 最高版本**，无更新可升
- ragas 0.4.3（2024 年底）依赖声明宽松（无版本上限），但代码本身还写着 `from langchain_community.chat_models.vertexai import ChatVertexAI`
- 2025 年后 langchain-community sunset / 拆包（`langchain-google-vertexai` 独立），新版不再有 `vertexai` 模块
- **结论：是 ragas 过时导致不兼容，不是 langchain 不兼容 ragas**

### 3. 行业最佳实践调研（2025-2026）

**分层评估**：轨迹（trajectory）+ 输出（output）+ 成本/延迟 三维一起评估
- **Trajectory Evaluation**：工具选择/参数正确性/路径效率/任务完成率
- **LLM-as-Judge**：DeepMind 2025 提出 Agent-as-a-Judge（ICML 2025）
- **工具调用级评估**：tool name/参数 schema/返回值消费/报错处理
- **成本/延迟约束**：token/延迟/重试成本
- **回归 + CI**：ground-truth 场景纳入 CI

**ragas 替代**：
- **DeepEval**（OSS，最接近 ragas 直接替代，pytest 原生，trajectory 支持好）
- **LangSmith / Langfuse / Arize Phoenix**（平台，观测+评估一体，trajectory 可视化）
- **Braintrust / Promptfoo**（平台，prompt 对比/回归/CI）
- **自研轻量 eval**（demo 现状）

> 关键点：没有统一的「下一个 ragas」，而是「观测平台 + 评估库 + 自研轨迹规则」组合。

### 4. 结论（写入分析文档）

- **不引入 ragas**（已停滞 + 依赖问题）
- **demo 继续自研 eval**，但补缺失层：LLM-as-Judge 语义指标 + Trajectory 评估
- 若要上平台，优先 Langfuse（week6 已有待办 #12）

### 5. 产出物

- `docs/courses/Agent评估行业实践与demo现状分析-2026-08-08.md`（新建，分析文档 + sources）

---

## 关键决策点（用户已定）

- ✅ 评估方向：「**先不改，帮我写分析**」— 不引入 ragas，先落盘行业实践分析
- ✅ 落盘分析文档到 `docs/courses/`

## 待办（下次继续）

- [ ] 评估体系改造方向最终确认（补 LLM-as-Judge / 补 trajectory / 上 Langfuse）后，出改造和实现计划
- [ ] week6 待办 #3（eval 接 CI）可在此基础上推进
- [ ] ragas_eval.py（scripts/week4 手写版）处置：删除 or 保留作参考

## 关联文件

- `docs/courses/Agent评估行业实践与demo现状分析-2026-08-08.md`（新建分析）
- `demo/eval/metrics.py` / `runner.py` / `ground_truth.json`（现状核查对象）
- `scripts/week4/ragas_eval.py`（手写 RAGAS，用户拒绝）
- `docs/week6/README.md`（待办 #3 eval 接 CI）

## 关联 session

- sessions/session-2026-08-08-项目2排产助手整理+三方核对+文档对齐.md（同日，项目2 定稿，其中六角色审阅含 RAGAS 表述失实风险）
