# 第一周 Day 3 收尾 + Day 4 学习清单

> **本周（自然周 7/6-7/10）= week1 收尾周**：代码已巩固提交，剩学习资料收尾。
> **今天 7/8 周三 = Day 3 收尾**（⑦ Prompt 工程剩半）
> **明天 7/9 周四 = Day 4**（原理速览 + Demo 打磨）
> **周五 7/10** = ⑦ 完结 + week2 预习（另清单 `docs/week2/week2_任务清单.md`）

---

## Day 3 收尾（7/8 周三，今天）— ⑦ Prompt 工程剩半

### 学习目标

把 Jimmy Song《提示词工程核心技术》剩下的一半读完，对照 ⑦ 的 7 项必须章节查漏，把 week1 Day3 代码里没落地的补进 Demo（CoT、版本管理）。

### 已读进度

- ✅ [OpenAI Prompt Engineering Guide](https://platform.openai.com/docs/guides/prompt-engineering)
- ✅ [Anthropic Prompt Engineering](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering)
- 🔵 [提示词工程核心技术 - Jimmy Song](https://jimmysong.io/zh/book/ai-handbook/prompt/techniques/) ⭐（剩下一半）

### 教材（今天读）

**主资料**（精读剩半）：
- ⭐ [提示词工程核心技术 - Jimmy Song](https://jimmysong.io/zh/book/ai-handbook/prompt/techniques/)

**中文补充**（自己读，我这边抓不回原文，读完把重点发我我帮提炼成代码）：
- [DeepSeek 提示词工程实践指南 - 百度开发者](https://developer.baidu.com/article/detail.html?id=3780820) - 培训路线图 ⑦ 中文资料清单第 2 项，DeepSeek 团队实战视角；重点关注 CoT / 结构化输出章节
- [从 Prompt 到上下文工程构建 Agent - 腾讯云](https://cloud.tencent.cn/developer/article/2586420) - 培训路线图 ⑦ 中文资料清单第 3 项，Agent 场景下 Prompt 如何演变到"上下文工程"；重点关注版本管理章节
- [提示词产品化设计 - 葡萄城](https://grapecity.csdn.net/6a292794662f9a54cb7c5829.html) - 培训路线图 ⑦ 中文资料清单第 4 项，Prompt 生产化视角；重点关注 A/B 测试 / 灰度发布 / 权限管控

> 三份的选源依据：`docs/培训路线图分析.md` 知识块 ⑦ 的"中文资料"表。综合浓缩摘要见同文档"重要章节摘要"格（含 System Prompt 万能模板、三层架构、Few-shot 黄金法则、Injection 防护等）。

**权威英文**（已读的可跳，需要复习就看）：
- [吴恩达 Prompt Engineering 课程](https://www.deeplearning.ai/short-courses/chatgpt-prompt-engineering-for-developers/)

### ⑦ 必须章节 7 项对照（自己勾选）

| # | 章节 | week1 Day3 代码已落地？ | 今天读什么 |
|---|------|------------------------|-----------|
| 1 | System Prompt 设计架构（角色+边界+约束+安全） | ✅ `build_system_level_prompt()` | 复习 Jimmy Song 对应章节 |
| 2 | 三层 Prompt 架构（系统/场景/用户） | ✅ 系统级/场景级/用户级三函数 | Jimmy Song 分层原理章节 |
| 3 | Few-shot 模板（3-5 对示例，+27%） | ✅ `SCENARIO_PROMPT` 末尾 | Jimmy Song "示例放最后"深度原因 |
| 4 | **CoT 思维链**（数学题准确率 +41%） | ❌ 未落地 | ⭐ **今天重点** |
| 5 | JSON Schema 输出约束 | ✅ `demo_structured_output()` | 复习即可 |
| 6 | **Prompt 版本管理 + A/B 测试** | ❌ 未落地 | ⭐ **今天重点** |
| 7 | Prompt Injection 防护（XML 隔离） | ✅ `build_user_message()` | 复习攻击手法样例 |

> 重点看 ④ CoT 和 ⑥ 版本管理——week1 Day3 代码里没落地，读完补进 Demo。

### CoT 思维链要点（章节 ④）

**核心**：让模型"逐步推理"再答，简单指令 `Let's think step by step` 或结构化 `<thinking>...</thinking>`；数学/多步推理准确率显著提升。

**参考读法**：
- Jimmy Song 里 CoT 一章
- [DeepSeek 提示词工程实践指南 - 百度开发者](https://developer.baidu.com/article/detail.html?id=3780820) 里 CoT 章节

**要点摘录**：
- Zero-shot CoT：加一句 "让我们逐步思考"
- Few-shot CoT：示例里也包含推理过程
- Self-Consistency：多次采样投票取最终答案

### 版本管理 + A/B 测试要点（章节 ⑥）

**核心**：生产 Prompt 是**代码资产**，需要词库管理系统——模板库 + 版本管理 + 灰度发布 + 调用统计 + 权限管控。

**参考读法**：
- Jimmy Song 里"生产级要点"一章
- [从 Prompt 到上下文工程构建 Agent - 腾讯云](https://cloud.tencent.cn/developer/article/2586420) 里版本管理章节
- [提示词产品化设计 - 葡萄城](https://grapecity.csdn.net/6a292794662f9a54cb7c5829.html)

**要点摘录**：
- Prompt 模板与版本号绑定（如 `system_v1.2`）
- A/B 测试：两版本按流量比例分发，比对指标
- 灰度发布：新版本 5% -> 20% -> 100%
- 调用统计：命中率、成功率、平均 Token

### 今日产出（学习笔记，可选）

- [ ] `docs/week1/day3_收尾_prompt_engineering.md`：把 Jimmy Song 剩半的重点摘要 + CoT + 版本管理架构图，写成一页笔记，方便 7/24 分享时回顾
- [ ] 决定明天要不要把 CoT + 版本管理落进代码（Day 4 补 Demo）

---

## Day 4（7/9 周四）— 原理速览 + Demo 打磨

### 学习目标

补齐 week1 落下的原理层——Token / Context Window / Temperature，理解模型"背后的物理量"；把 CoT / 版本管理（⑦ 未落地部分）补进 week1 Demo。

### 教材

#### Token / 分词

**权威**：
- ⭐ [OpenAI Tokenizer 工具（可视化）](https://platform.openai.com/tokenizer) - 直接输入文本看 token 切分
- [tiktoken - OpenAI 官方 Python 分词库](https://github.com/openai/tiktoken)

**中文**：
- [大模型 Token 与分词器详解 - 知乎](https://zhuanlan.zhihu.com/p/643434021)
- [BPE 分词算法（原理）- 知乎](https://zhuanlan.zhihu.com/p/424631681)

**要点**：Token ≠ 字符 ≠ 单词；中文一个汉字约 1.5-2 token；BPE/BBPE 分词原理；Token 计费口径（输入+输出分开）。

#### Context Window / 上下文窗口

**权威**：
- ⭐ [Anthropic Long context tips](https://docs.anthropic.com/en/docs/build-with-claude/context-windows) - 长上下文最佳实践
- [OpenAI Model 页 context 列](https://platform.openai.com/docs/models)

**中文**：
- [内存管理与上下文优化 - 腾讯云](https://cloud.tencent.cn/developer/article/2557090) ⭐（LangGraph 相关，跟你 week3 铺路）
- [从 Prompt 到上下文工程构建 Agent - 腾讯云](https://cloud.tencent.cn/developer/article/2586420)

**要点**：Window 大小影响什么（能塞多少内容）；Attention 复杂度 O(n²) 导致长窗口成本翻倍；文档摘要/滑动窗口/结构化召回是三种压缩策略。

#### Temperature / 采样参数

**权威**：
- [OpenAI Chat Completions API 参数](https://platform.openai.com/docs/api-reference/chat/create) - temperature / top_p / top_k / frequency_penalty / presence_penalty
- [Anthropic Messages API 参数](https://docs.anthropic.com/en/api/messages)

**中文**：
- [大模型采样参数完全指南 - 知乎](https://zhuanlan.zhihu.com/p/653927240)
- Jimmy Song ⑦ 里"温度参数"章节

**要点**：
- Temperature 0.0-0.3：事实查询、代码生成
- Temperature 0.5-0.7：通用任务
- Temperature 0.8-1.2：创意写作、多样性
- top_p 和 temperature 二选一，不要同时改
- top_k 只在 Anthropic API 里，OpenAI 没这参数

### 建议今日结构

**上午（2h 读）**：
1. Token（30min）+ Tokenizer 工具亲手玩几次
2. Context Window（40min）
3. Temperature / 采样（50min）

**下午（4h 写代码，二选一）**：
- **方案 A（推荐）**：给 week1 Day3 代码补 CoT + 版本管理
  - CoT：`SCENARIO_PROMPT` 里加 `<thinking>` 引导 + 一个数学/推理场景的 Few-shot
  - 版本管理：Prompt 抽成 `prompts/system_v1.py`、`prompts/scenario_v1.py`，用变量注入日期，加 `PROMPT_VERSION = "v1.0"` 常量
- **方案 B**：只做 Token 计数实验——用 tiktoken 统计 week1 三个 demo 的输入/输出 token，估算成本

### 今日产出

- [ ] `docs/week1/day4_guide.md`：Token/Context/Temperature 一页笔记（对齐 day1-3 guide 格式）
- [ ] （可选）`scripts/week1/day4_principles.py`：Token 计数 demo + Temperature 对比实验（同 prompt 跑 0.3/0.7/1.0，看输出差异）
- [ ] （可选）week1 Demo 加 CoT + 版本管理

---

## 周五 7/10 预告

- ⑦ 彻底完结（若 Day3+Day4 还有落下的收尾）
- week2 预习：装 Milvus / 读 All-in-RAG README / 起 embedding 模型
- 详情见 `docs/week2/week2_任务清单.md`

---

## 面试速记卡预热（Day 4 后可补）

```
Q: Token 和字符什么关系？
A: Token 是模型的最小处理单元，用 BPE/BBPE 分词。英文平均 4 字符/token，
   中文 1 汉字≈1.5-2 token。tiktoken 可直接查看。

Q: Context Window 越大越好？
A: 不是。Attention 是 O(n²) 复杂度，窗口翻倍 -> 计算/延迟/成本翻 4 倍。
   实际用摘要压缩 + 检索召回替代硬塞。

Q: Temperature 怎么选？
A: 事实/代码 0.1-0.3；通用 0.5-0.7；创意 0.8-1.2。
   不要同时改 top_p，二选一。

Q: CoT 什么时候用？
A: 多步推理/数学题必用。Zero-shot 加"逐步思考"即可，Few-shot 里示例
   也要含推理过程。

Q: 生产 Prompt 怎么管？
A: 抽成模板文件 + 版本号 + A/B 测试 + 灰度发布 + 调用统计。当代码资产管，
   不是散落在字符串里。
```
