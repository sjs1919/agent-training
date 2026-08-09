# Session: demo 三层评估体系实现 + 全量测试 + 回测

> 日期：2026-08-09
> 话题：三层评估（工具/轨迹/语义）+ 可视化报告 + 全 demo 测试 + 回测模块实现
> 状态：全部完成，128 测试全绿，真实 LLM 评估受主 provider 配额影响

---

## 本次完成

### 1. 三层评估体系（替换手写 eval）

| 层 | 文件 | 指标 |
|----|------|------|
| 工具层 | `eval/metrics.py` | 工具 F1 + 完整性 + 订单召回 + **min_tools_called**（R6 硬伤修复） |
| 轨迹层 | `eval/trajectory.py` + `trajectory_capture.py` | 路径效率 + 重试质量 + 循环检测 |
| 语义层 | `eval/judge.py` + `judge_prompt.py` | 自研 LLM-as-Judge：faithfulness + answer_relevancy |

### 2. 可视化报告

`eval/report.py` 单页 HTML，三层指标 + 通过/失败 + 循环标记。

### 3. 全 demo 单元测试（TDD，codegraph 驱动）

- 128 passed：eval 41 + tools 30 + graph 10 + rag 11 + observability 11 + auth 11 + cache 8 + backtest 6
- codegraph 探索三份报告（工具层/图执行层/RAG+缓存+鉴权+观测层）驱动测试设计
- pytest 基础设施：`pytest.ini` + `conftest.py`（agent-training 根加 sys.path，`from demo.*` 导入）

### 4. 一键自动化脚本

`run_all_tests.py` + `test_demo.sh`：pytest 全量 → 三层评估 → HTML 报告。

### 5. 回测模块（此前无回测概念）

`backtest/` 用 `data/历史延期记录.txt` 的 5 个真实案例（设备故障/物料延迟/质检报废/加急插单/设计变更），让 Agent 复盘，按人工结论覆盖度评分。

### 6. 真实 LLM 评估验证

- **发现主 provider 火山豆包 429 配额超限**（AccountQuotaExceeded）
- DeepSeek 备用 provider 成功兜底（L1 缓存命中多次）→ **主备 fallback 架构验证成立**
- 回归基线待账户恢复后重跑

---

## 发现并修复的真实 bug

1. **CostTracker.record 死锁**（严重）：`threading.Lock` 非可重入，`record()` 锁内调 `self.total_cost` 二次加锁 → 任何真实 LLM 调用卡死。独立脚本复现，已修复。
2. **evaluate_results 死循环风险**：纯文本轮 iteration 不递增，`needs_more` 残留 → should_continue 多绕，消息膨胀后死循环。数据充足时清标记，已修复。

## 发现但未修

- 火山豆包配额超限（账户层，需恢复）
- orders.csv 缺 `客户等级`/`工艺` 列（R7 参数已实现但数据缺列）

## 关键决策点（用户已定）

- ✅ 自研 LLM-as-Judge（不引 ragas，已停滞）
- ✅ 轨迹评估做到路径效率/重试分析
- ✅ 做可视化 HTML 报告
- ✅ 允许真实调用 LLM（实际触发主 provider 配额告警）
- ✅ git 自主提交

## 产出物

- `demo/eval/` 三层评估 + 报告 + 测试
- `demo/backtest/` 回测模块
- `demo/run_all_tests.py` / `test_demo.sh` 自动化脚本
- `docs/superpowers/plans/2026-08-08-ragas升级-三层评估体系.md`（实现计划）
- `docs/week6/demo-评估改造实现过程定位-2026-08-09.md`（实现过程定位）

## 待办（下次继续）

- [ ] 火山豆包配额恢复后重跑 `python -m demo.eval.runner --report` 拿真实回归基线
- [ ] 接 CI（用户决定 GitLab / 本地）
- [ ] 回测真实跑（需 LLM）
- [ ] orders.csv 补 `客户等级`/`工艺` 列

## 关联 session

- sessions/session-2026-08-08-Agent评估体系现状与行业实践分析.md（昨日：现状梳理 + 行业实践）
