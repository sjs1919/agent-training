# 第一周 · Day 3 扩展 — Jimmy Song ⑦ 提示词工程收尾笔记

> **日期**：2026-07-10
> **前置**：day3_guide.md（三层 Prompt 架构 + 日期注入 + XML 隔离已落地）
> **本文定位**：Jimmy Song《提示词工程核心技术》整本读完后的收尾笔记，记录 ⑧ MCP 集成 + ⑨ 高级技巧 两章的读后感，以及全书学完后的沉淀。
> **落地状态**：本次仅完成读书 + 笔记，**代码落地（Jinja2 / PromptOps / CoT）延后到 Day 4 或周末**。

---

## 一、章节阅读进度对照

| 章 | 章节名 | 阅读状态 | 代码落地状态 |
|:---:|--------|:---:|:---:|
| 1 | 概述 | ✅ 已读 | — |
| 2 | 核心技术 | ✅ 已读 | 部分落地（day3_system_prompt.py） |
| 3 | 输出配置 | ✅ 已读 | 部分落地（JSON Schema demo） |
| 4 | 最佳实践 | ✅ 已读 | 部分落地（三层架构） |
| 5 | Jinja2 提示词模板 | ✅ 已读 | ❌ 未落地（当前 f-string） |
| 6 | 面向工程环境的设计 | ✅ 已读 | ❌ 未落地（prompts 未成包） |
| 7 | PromptOps 工作流 | ✅ 已读 | ❌ 未落地（无版本号/灰度） |
| 8 | MCP 集成 | ✅ 已读（本次） | 延后到 week3 |
| 9 | 高级技巧 | ✅ 已读（本次） | 待评估 |

**整本 ⑦ 阅读进度：100%（9/9 章）** ✅

---

## 二、⑧ MCP 集成 · 读后感

> **主资料**：⭐ [提示词工程核心技术 - Jimmy Song · MCP 集成章](https://jimmysong.io/zh/book/ai-handbook/prompt/techniques/)

### 2.1 三个自问自答

**Q1：Jimmy Song 视角下，MCP 和 Prompt 的接口点在哪？Prompt 怎么"知道"有哪些 MCP 工具可用？**

<!-- TODO(你填)：用自己的话回答，1-3 句 -->

---

**Q2：MCP Server 暴露的工具，`description` 字段和 System Prompt 的"能力边界"是什么关系？谁写谁？**

<!-- TODO(你填)：用自己的话回答，1-3 句 -->

---

**Q3：Jimmy Song 讲的 MCP 用法 vs OpenAI Function Calling（week1 Day2 已实现）有什么本质差异？**

<!-- TODO(你填)：用自己的话回答，1-3 句 -->

---

### 2.2 读完带回

**从 Prompt 工程视角看，MCP 到底解决了什么 Function Calling 没解决的问题？**（一段话）

<!-- TODO(你填) -->

---

**一个疑问**（可以写不确定）：week3 用 MCP 重构 week1/2 的工具，会比现在的 `TOOLS` 列表好在哪？

<!-- TODO(你填) -->

---

## 三、⑨ 高级技巧 · 读后感

> **主资料**：⭐ [提示词工程核心技术 - Jimmy Song · 高级技巧章](https://jimmysong.io/zh/book/ai-handbook/prompt/techniques/)

### 3.1 三类内容速记

**① CoT / Self-Consistency / ToT 推理增强类**

<!-- TODO(你填)：这章讲了哪些？你觉得哪个最实用？为什么？ -->

---

**② Prompt Injection 高级攻击 & 防御升级**

week1 目前只做了 XML 标签隔离。Jimmy Song 讲的高级攻击/防御里，还有哪些是 XML 隔离不足以覆盖的？

<!-- TODO(你填) -->

---

**③ 其它零碎但关键的技巧**（如少样本示例排序、指令位置、否定 Prompt 效果差等）

<!-- TODO(你填)：列 2-4 条你记住的 -->

---

### 3.2 读完带回

**3 条可以直接落到 week1 Demo 的技巧**（每条一句话说做什么）：

1. <!-- TODO(你填) -->
2. <!-- TODO(你填) -->
3. <!-- TODO(你填) -->

---

**1 条不适合当前场景但值得记住的**（写进面试速记卡）：

<!-- TODO(你填) -->

---

## 四、整本 ⑦ 读完的收尾自问

**Q1：⑦ 提示词工程整本读完，我现在最有把握的是 ______**

<!-- TODO(你填) -->

---

**Q2：还没把握的是 ______**

<!-- TODO(你填) -->

---

**Q3：落到 week1 Demo 代码的抓手是 ______**

<!-- TODO(你填) -->

---

## 五、后续落地清单（延后执行）

本次只完成读书 + 笔记，以下代码落地任务**延后**，不阻塞 Day 4 主线：

| 优先级 | 任务 | 预计耗时 | 触发时机 |
|:---:|------|:---:|------|
| P0 | Jinja2 模板 + `prompts/` 包抽取 | 1.5h | 周末 or Day 5 复盘时 |
| P1 | Prompt 版本号 + 最小 A/B 分流 | 1h | 同上 |
| P1 | CoT `<thinking>` 引导 + demo 4 | 1h | 同上 |
| P2 | ⑨ 高级技巧中的其它落地项 | 视 §3.2 结论 | 同上 |

**理由**：Day 4 主线是"Token / Context / Temperature 原理速览 + week2 预习"（见 `day3收尾_day4_清单.md`），代码落地不能挤占。

---

## 六、下一步

- ✅ 本文（day3_extension.md）完成后，⑦ 提示词工程 100% 收尾
- ⏭️ 进入 Day 4：原理速览（Token / Context / Temperature）
- ⏭️ week2 预习：All-in-RAG + Milvus 环境
