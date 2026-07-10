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

Prompt 通过 MCP Client 在会话建立后调用 `tools/list` 拿到可用工具集合；工具名、`description`、参数 schema 会被整理进 System Prompt（或作为 tool definitions 传给模型）。所以模型"知道"自己能调什么、每个工具是干什么的。

---

**Q2：MCP Server 暴露的工具，`description` 字段和 System Prompt 的"能力边界"是什么关系？谁写谁？**

`description` 由 MCP Server / 工具开发者写，描述单个工具的能力、参数和返回值；System Prompt 由应用开发者写，定义 Agent 的整体身份、边界和调用策略。两者是互补关系：System Prompt 说"你能做什么"，工具 description 说"这个工具具体怎么做"。

---

**Q3：Jimmy Song 讲的 MCP 用法 vs OpenAI Function Calling（week1 Day2 已实现）有什么本质差异？**

Function Calling 是模型能力层（让模型输出 JSON 参数去调函数），但工具定义、发现、调用、生命周期都散落在代码里；MCP 是协议层，把这些约定标准化，让工具可以独立部署、发现、替换和复用，与具体模型 provider 解耦。

---

### 2.2 读完带回

**从 Prompt 工程视角看，MCP 到底解决了什么 Function Calling 没解决的问题？**（一段话）

MCP 把 Function Calling 里"工具怎么定义、怎么发现、怎么调用、怎么维护"这些散在代码里的约定，抽象成一套标准协议，让工具变成可独立开发、测试、部署和度量的服务。Prompt 工程从"写死 TOOLS 列表"变成"描述 Agent 能力边界 + 引用外部工具目录"，工具的变更不再需要改 Agent 主代码。

---

**一个疑问**（可以写不确定）：week3 用 MCP 重构 week1/2 的工具，会比现在的 `TOOLS` 列表好在哪？

1. **可管理、可工程化**：工具与 Agent 代码解耦，改工具实现不用改 Agent 主流程。
2. **可测试**：工具作为独立服务可以单独测试、mock、版本化。
3. **可度量**：MCP 层可以统一记录工具调用次数、成功率、延迟、token 消耗等量化指标。
4. **可复用**：同一套 MCP Server 可被不同 Agent / 不同客户端（Claude Code、Cursor 等）共用。

---

## 三、⑨ 高级技巧 · 读后感

> **主资料**：⭐ [提示词工程核心技术 - Jimmy Song · 高级技巧章](https://jimmysong.io/zh/book/ai-handbook/prompt/techniques/)

### 3.1 三类内容速记

**① CoT / Self-Consistency / ToT 推理增强类**

- **Zero-shot CoT**：在 Prompt 末尾加"让我们逐步思考"，让模型先推理再回答。
- **Few-shot CoT**：示例里包含推理过程，模型会模仿这种格式。
- **Self-Consistency**：多次采样，对结果投票，降低偶发幻觉。
- **ToT（Tree of Thoughts）**：在多个推理路径中搜索、评估、回溯，适合复杂决策。

最实用的是 **Few-shot CoT**：在 week1 的订单调度场景里，给模型一个"先分析约束、再排优先级、最后输出"的示例，能明显提升多条件排序的稳定性。

---

**② Prompt Injection 高级攻击 & 防御升级**

week1 目前只做了 XML 标签隔离。Jimmy Song 里提到的高级攻击还包括：

- **间接提示注入**：攻击者把恶意指令藏在检索内容、工具返回数据、外部文档里，Agent 读取后执行。
- **越狱 / 角色扮演绕过**：用情感操纵、虚构场景让模型忽略原规则。
- **分隔符 / 编码绕过**：用特殊字符、Unicode、注释符试图逃出 XML 标签。

对应的防御升级：

- 对**所有外部输入**（不仅是用户输入，还包括工具返回值、检索片段）做隔离或摘要。
- 给工具加**最小权限**和**危险操作人工确认**。
- 对模型输出做**校验与过滤**，不合规时拒绝或重试。
- 高敏感操作走沙箱或白名单。

---

**③ 其它零碎但关键的技巧**

- **示例排序**：Few-shot 示例按难度递增，最难的放最后，模型遵从度更高。
- **指令位置**：关键指令放在 Prompt 开头或结尾，中间位置容易被模型忽略。
- **避免否定式**："不要编造订单"效果差，改成"只基于 query_orders 返回的真实数据回答"。
- **明确格式**：用 XML 标签、JSON schema、Markdown 表格等明确输出格式，比模糊描述稳定。

---

### 3.2 读完带回

**3 条可以直接落到 week1 Demo 的技巧**（每条一句话说做什么）：

1. **加 `<thinking>` 引导**：在场景级 Prompt 里让模型先分析日期、优先级等约束，再输出调度建议。
2. **Few-shot 示例带推理过程**：给多条件排序场景一个"先按交期、再按客户等级"的完整思考示例。
3. **结构化输出加校验重试**：JSON Schema 输出失败时，回退到文本回答并记录失败，不让程序崩。

---

**1 条不适合当前场景但值得记住的**（写进面试速记卡）：

**Self-Consistency**：对关键生产调度决策，可以多次采样取多数结果，降低单次模型幻觉带来的风险。培训 Demo 里单条输出足够，但生产决策链路中值得引入。

---

## 四、整本 ⑦ 读完的收尾自问

**Q1：⑦ 提示词工程整本读完，我现在最有把握的是 ______**

三层 Prompt 架构（系统级 / 场景级 / 用户级）+ 当前日期注入修年份 bug + XML 标签隔离防 Prompt Injection + JSON Schema 输出约束。

---

**Q2：还没把握的是 ______**

- MCP Server 的具体实现细节（stdio / SSE 传输、生命周期管理、权限模型）。
- Prompt Caching 的成本测算和命中策略。
- 生产级 A/B 测试的指标设计（成功率、token 成本、延迟、用户满意度怎么加权）。

---

**Q3：落到 week1 Demo 代码的抓手是 ______**

把 `day3_system_prompt.py` 里硬编码的 f-string Prompt 抽成 Jinja2 模板 + `prompts/` 包，引入版本常量，再加一个带 `<thinking>` 引导的场景模板和最小 A/B 分流。

---

## 五、代码落地状态

| 优先级 | 任务 | 状态 |
|:---:|------|:---:|
| P0 | Jinja2 模板 + `prompts/` 包抽取 | ✅ 已完成 |
| P1 | Prompt 版本号 + 最小 A/B 分流 | ✅ 已完成（v1 / v2_cot，按 user_id MD5 稳定分桶，v2 占 20%） |
| P1 | CoT `<thinking>` 引导 + demo 4 | ✅ 已完成（`scenario_v2_cot.jinja` + 多约束排优先级演示） |
| P2 | ⑨ 高级技巧中的其它落地项 | 待评估（Self-Consistency / ToT 暂不进 week1 Demo） |

---

## 六、下一步

- ✅ 本文（day3_extension.md）已补齐，⑦ 提示词工程 100% 收尾
- ✅ C 代码落地完成
- ⏭️ 进入 B：Day 4 原理速览（Token / Context / Temperature）
- ⏭️ week2 预习：All-in-RAG + Milvus 环境

