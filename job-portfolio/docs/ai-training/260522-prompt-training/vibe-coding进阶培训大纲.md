# Vibe Coding 进阶培训大纲

> 目标受众：已完成一个初级 AI 编程项目，希望系统性提升协作效率的研发人员
> 主力工具：Claude Code
> 形式：两期线下培训 + 课后实践

---

## 阅读执行计划表

> 按优先级顺序阅读，读完一项勾选一项。全部完成后通知我更新状态。
>
> **团队工具栈**：Claude Code CLI（主力）+ Trae IDE（辅助）

### 第一阶段：官方文档（工具原理，必读）

| 序号 | 状态 | 阅读内容 | 对应培训 | 预计时间 | 优先级 |
|:----:|:----:|----------|----------|:--------:|:------:|
| 1 | [ ] | [Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)（[Overview](https://docs.anthropic.com/en/docs/claude-code/overview) + [Settings](https://docs.anthropic.com/en/docs/claude-code/settings) + [Hooks](https://docs.anthropic.com/en/docs/claude-code/hooks) + [CLAUDE.md](https://docs.anthropic.com/en/docs/claude-code/claude-code-tutorial#step-3-create-a-claude-md-file)） | 第二期「深度工作流」 | 2-3h | **必读** |
| 2 | [ ] | [Anthropic Prompt Engineering Guide](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview) | 第一期「5条铁律」 | 1-2h | **必读** |
| 3 | [ ] | [MCP 协议文档](https://modelcontextprotocol.io) | 第二期「MCP 接入」 | 1h | **必读** |

### 第二阶段：《AI 编程实战三卷书》章节精读

> 以下按 **P0（必读）/ P1（重要）/ P2（按需）/ P3（暂缓）** 四级优先级排列。每章附 1 句话摘要，供你快速判断是否深入。

#### P0 必读 — 与当前工作流直接相关

| 状态 | 章节 | 链接 | 一句话摘要 | 为什么必读 |
|:----:|------|------|-----------|-----------|
| [ ] | 卷一·Ch8: Claude Code — CLI Agent 之王 | [链接](https://book.aibuzhiyu.com/tools/claude-code/index.html) | Subagent/Command/Skill/Hook/MCP/Memory/Checkpoint 核心概念详解 + 快速上手 | 你们的主力工具，深度使用必读。涵盖 Skill 配置、Hook 自动化、MCP 扩展等培训未涉及的内容 |
| [ ] | 卷一·Ch5: 上下文管理 | [链接](https://book.aibuzhiyu.com/methods/context-management.html) | 精确喂入 vs 全量投喂、项目配置文件作为最高效上下文、长对话断点续传策略 | 200K tokens 怎么高效利用，直接决定 Claude Code 的产出质量 |
| [ ] | 卷二·Ch12: 调试方法论 | [链接](https://book.aibuzhiyu.com/methods/debugging.html) | 四阶段调试法：收集证据→分析根因→验证假设→精确修复。告别"贴报错→AI猜"的低效模式 | 作者说这是"最被低估的能力，95%用户从来没让AI系统化调过bug" |
| [ ] | 卷二·Ch19: Claude Code 陷阱 | [链接](https://book.aibuzhiyu.com/pitfalls-src/claude-code.html) | 31个深度陷阱，每条按"症状→根因→出坑→预防"四段式展开。上下文溢出、文件改一半、测试幻觉等 | 用过都会遇到，直接止损。建议先快速过一遍，遇到对应症状再细读 |
| [ ] | 卷二·Ch26: Trae — 字节出品免费版 | [链接](https://book.aibuzhiyu.com/tools/trae/index.html) | Builder/Chat/补全三种模式、Rules 配置、@引用精确指定上下文。国内直连+免费额度充足 | 你们的辅助工具，了解 Trae 的 Rules 和 @引用能提升辅助看代码的效率 |

#### P1 重要 — 与培训内容互补，提升效率

| 状态 | 章节 | 链接 | 一句话摘要 | 什么情况下优先读 |
|:----:|------|------|-----------|-----------------|
| [ ] | 卷一·Ch3: 提示词工程 | [链接](https://book.aibuzhiyu.com/methods/prompting.html) | 和培训1的"5条铁律+四种模式"内容重合度高，但补充了更多场景化模板 | 如果你觉得培训1的内容不够，需要更多 Prompt 模板时读 |
| [ ] | 卷二·Ch11: 代码审查 | [链接](https://book.aibuzhiyu.com/methods/code-review.html) | 审查五维度（安全/正确性/性能/可维护性/测试）+ 分级输出标准，不是"帮我看看有没有bug" | 需要建立团队 Code Review 规范，或让 AI 系统化做审查时读 |
| [ ] | 卷二·Ch13: 测试策略 | [链接](https://book.aibuzhiyu.com/methods/testing.html) | AI 辅助生成测试、覆盖边界情况、测试作为安全网。与培训2的"AI辅助TDD"章节互补 | 团队要落地 AI 辅助测试，或覆盖率不达标时读 |
| [ ] | 卷一·Ch4: 需求拆解 | [链接](https://book.aibuzhiyu.com/methods/task-decomposition.html) | 复杂任务拆分为 AI 可执行的子任务，明确每步的输入输出和验收标准 | 经常遇到"AI改了一半发现方向错了"时读 |
| [ ] | 卷二·Ch16: Claude Code + Cursor 协作 | [链接](https://book.aibuzhiyu.com/workflows-src/claude-code-cursor.html) | 分工原则：Claude Code 做"重活"（架构/重构/调试/测试），Cursor 做"日常"（编码/UI/快速修改） | 你们用 Trae 替代 Cursor，协作思路可直接参考：Claude Code 做重活，Trae 做日常 |

#### P2 按需 — 特定场景触发

| 状态 | 章节 | 链接 | 一句话摘要 | 什么情况下读 |
|:----:|------|------|-----------|-------------|
| [ ] | 卷二·Ch18: 陷阱总览 | [链接](https://book.aibuzhiyu.com/pitfalls-src/index.html) | 4款主流工具31个陷阱的速查目录，快速定位你正在踩的坑 | 遇到诡异问题时先来这查 |
| [ ] | 卷二·Ch14: 多工具选型指南 | [链接](https://book.aibuzhiyu.com/workflows-src/tool-selection.html) | 9款工具的选型矩阵：什么场景用谁、怎么组合、预算怎么分配 | 想扩展工具栈（如引入 Gemini CLI 的 2M 上下文）时读 |
| [ ] | 卷二·Ch15: 实战场景脚本 | [链接](https://book.aibuzhiyu.com/workflows-src/scenarios.html) | 具体场景的标准化脚本模板：新项目初始化、技术债务清理、紧急热修等 | 需要可复制的标准化工作流时读 |
| [ ] | 卷三·Ch29: 安全注意事项 | [链接](https://book.aibuzhiyu.com/methods/security.html) | AI 代码的高频安全风险：敏感信息硬编码、SQL注入、缺少权限校验、XSS等 | 项目涉及敏感数据、需要做安全审计时读 |

#### P3 暂缓 — 当前工具栈无关，以后需要再读

| 状态 | 章节 | 链接 | 一句话摘要 | 为什么暂缓 |
|:----:|------|------|-----------|-----------|
| [ ] | 卷一·Ch6-7,9: Cursor / Copilot / Codex 工具篇 | [链接](https://book.aibuzhiyu.com/tools/cursor/index.html) 等 | 各工具的核心概念、快速上手、最佳实践 | 你们没在用这些工具 |
| [ ] | 卷二·Ch20-22: Cursor / Copilot / Aider 陷阱 | [链接](https://book.aibuzhiyu.com/pitfalls-src/cursor.html) 等 | 对应工具的专属陷阱合集 | 没在用就不需要 |
| [ ] | 卷二·Ch23-25,27: Aider / Gemini CLI / Windsurf / Kiro | [链接](https://book.aibuzhiyu.com/tools/aider/index.html) 等 | 小众但有特定优势的工具详解 | 当前工具栈已满足需求，未来扩展时再读 |
| [ ] | 卷三·Ch28,30: 卷三·序 / OpenClaw Agent 框架 | [链接](https://book.aibuzhiyu.com/v3-intro.html) 等 | 团队级 AI 编程架构：权限管控、审计日志、多 Agent 协作 | 目前团队规模不需要，架构升级时再读 |
| [ ] | 卷一·Ch2 / 别册: 9 工具速查表 / 更新日志 | [链接](https://book.aibuzhiyu.com/cheatsheet.html) | 9款工具的核心特性快速对比 | 已选定工具栈，不需要再对比 |

### 第三阶段：延伸阅读（灵感补充 + 战略视角）

| 序号 | 状态 | 阅读内容 | 预计时间 | 优先级 |
|:----:|:----:|----------|:--------:|:------:|
| 4 | [ ] | [Anthropic Cookbook](https://github.com/anthropics/anthropic-cookbook)（按需选读章节：Caching / Tool Use / Vision） | 0.5h/章 | 参考 |
| 5 | [ ] | 社区资源（[Awesome Prompts](https://github.com/doggydotnet/awesome-claude-prompts) / [Cursor Directory](https://cursor.directory) / [Reddit](https://reddit.com/r/ClaudeAI)） | 灵活 | 浏览 |
| 6 | [ ] | [Martin Fowler: Exploring GenAI](https://martinfowler.com/articles/exploring-gen-ai.html) | 0.5h | 浏览 |

### 传统软件工程资料（大纲正文已覆盖，按需深入）

| 序号 | 状态 | 阅读内容 | 大纲对应位置 | 什么情况下读 |
|:----:|:----:|----------|-------------|-------------|
| 7 | [ ] | TDD 相关（[Martin Fowler 简明解释](https://martinfowler.com/bliki/TestDrivenDevelopment.html) / [xUnit Test Patterns](https://www.amazon.com/xUnit-Test-Patterns-Refactoring-Code/dp/0131495054)） | 第187-209行 | 团队要落地 AI 辅助测试时 |
| 8 | [ ] | BDD / Spec 相关（[Cucumber BDD 指南](https://cucumber.io/docs/bdd/) / [Gherkin 语法](https://cucumber.io/docs/gherkin/) / [Specification by Example](https://www.amazon.com/Specification-Example-Successful-Deliver-Software/dp/1617290084)） | 第212-237行 | 产品团队配合写 Spec 时 |
| 9 | [ ] | DDD 相关（[Eric Evans 原著](https://www.amazon.com/Domain-Driven-Design-Tackling-Complexity-Software/dp/0321125215) / [Vaughn Vernon 实践指南](https://www.amazon.com/Implementing-Domain-Driven-Design-Vaughn-Vernon/dp/0321834577) / [DDD Community](https://dddcommunity.org) / [Martin Fowler DDD 概述](https://martinfowler.com/tags/domain%20driven%20design.html)） | 第240-264行 | 复杂业务系统重构建模时 |
| 10 | [ ] | GoF 设计模式（[Refactoring.Guru 可视化入门](https://refactoring.guru/design-patterns) / [SourceMaking](https://sourcemaking.com/design_patterns)） | 第269-278行 | AI 推荐了不认识的模式时 |
| 11 | [ ] | 架构相关（[Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) / [微服务](https://martinfowler.com/articles/microservices.html) / [六边形架构](https://alistair.cockburn.us/hexagonal-architecture/)） | 第280-289行 | 架构评审或系统拆分时 |

---

## 第一期：Prompt 精修与模板化

**时长**：45 分钟  
**人数**：5-10 人  
**前置要求**：有使用 Claude Code 完成至少一个功能模块的经验

### 时间分配

| 环节 | 时长 | 形式 |
|------|------|------|
| 开场：两期培训规划与目标 | 5 min | 讲解 |
| 核心原则：5 条铁律 | 10 min | 讲解 + 对比演示 |
| 四种标准化 Prompt 模式 | 8 min | 讲解 |
| Prompt 模板参数化 | 7 min | 讲解 + 实操 |
| 项目配置文件入门（CLAUDE.md） | 4 min | 讲解 |
| 实战：学员案例改写 | 6 min | 互动 + Live Demo |
| Q&A + 第二期引子 | 5 min | 互动 |

### 内容要点

- **5 条铁律**：具体>模糊、约束>自由、分步>一次、示例>描述、参考>从零
- **四种模式**：分析模式（先看后说）、实现模式（明确需求）、修复模式（给证据）、审查模式（定范围）
- **模板参数化**：把验证好的 prompt 抽象为可替换变量的模板；团队模板库的建立
- **CLAUDE.md**：项目级配置文件的作用、基本结构、与 `.cursorrules` 的区别
- **反模式提醒**：融入实战环节，不再单独列表

### 交付物

- 每人 3 个可复用的参数化 Prompt 模板
- 团队共享模板库初版
- 课后作业：提交 1 个自己的"改造前 vs 改造后"Prompt 案例

---

## 第二期：项目级 AI 协作工程

**时长**：60 分钟  
**人数**：5-10 人  
**前置要求**：完成第一期 + 提交课后作业

### 时间分配

| 环节 | 时长 | 形式 |
|------|------|------|
| 开场：作业点评 + 问题收集 | 5 min | 讲解 + 互动 |
| 多轮对话状态管理 | 12 min | 讲解 + 演示 |
| 大型代码库导航策略 | 10 min | 讲解 + 演示 |
| AI 辅助 TDD | 10 min | 讲解 + Live Demo |
| Claude Code 深度工作流 | 8 min | 讲解 |
| 完整功能开发演练 | 12 min | 实战 |
| Q&A + 模板沉淀 | 3 min | 互动 |

### 内容要点

- **多轮状态管理**：对话进度追踪、断点续传、`/clear` 的正确用法、用文件传递上下文
- **大型代码库**：让 AI 先建项目地图、跨模块依赖分析、改动风险评估、精确引用 vs 全量投喂
- **AI 辅助 TDD**：先写测试再写实现、Prompt AI 覆盖边界情况、测试作为安全网
- **Claude Code 深度工作流**：
  - `CLAUDE.md` 进阶写法（团队协作规范）
  - `settings.json` 实战：hooks 配置、权限自动化
  - MCP 接入概念：扩展 Claude 的能力边界
  - 高级命令：`/ask` `/test` `/commit` 等最佳实践

### 交付物

- 团队级 AI 协作工作流文档
- 多场景 Prompt 模板库 v1.0
- 状态管理 Checklist
- 代码库导航 SOP

---

## 推荐学习资料（Claude Code 用户）

### 官方文档（必读）

| 资源 | 链接 | 说明 |
|------|------|------|
| Anthropic Prompt Engineering Guide | [docs.anthropic.com](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview) | 最权威的 Prompt 工程系统教程 |
| Anthropic Cookbook | [github.com/anthropics/anthropic-cookbook](https://github.com/anthropics/anthropic-cookbook) | 官方代码示例库，覆盖 Caching / Tool Use / Vision |
| Claude Code 官方文档 | [docs.anthropic.com/claude-code](https://docs.anthropic.com/en/docs/claude-code/overview) | 命令系统、CLAUDE.md、settings.json、hooks 完整说明 |
| Claude Code GitHub | [github.com/anthropics/claude-code](https://github.com/anthropics/claude-code) | Release Notes、已知问题、Feature Request |
| MCP 协议文档 | [modelcontextprotocol.io](https://modelcontextprotocol.io) | 扩展 Claude 能力边界的标准协议 |

### 配置参考

| 资源 | 链接 | 说明 |
|------|------|------|
| Claude Code Settings | [官方文档](https://docs.anthropic.com/en/docs/claude-code/settings) | settings.json / settings.local.json 全配置项 |
| Hooks 配置 | [官方文档](https://docs.anthropic.com/en/docs/claude-code/hooks) | 自动化行为：提交前执行、权限自动放行等 |
| CLAUDE.md 编写指南 | [官方文档](https://docs.anthropic.com/en/docs/claude-code/claude-code-tutorial#step-3-create-a-claude-md-file) | 项目级配置文件的最佳实践 |

### 社区与案例

| 资源 | 链接 | 说明 |
|------|------|------|
| Awesome Claude Prompts | [github](https://github.com/doggydotnet/awesome-claude-prompts) | 场景化 Prompt 集合 |
| Cursor Directory | [cursor.directory](https://cursor.directory) | `.cursorrules` 模板库，内容可改写成 `CLAUDE.md` 使用 |
| r/ClaudeAI Reddit | [reddit.com/r/ClaudeAI](https://reddit.com/r/ClaudeAI) | 社区讨论、技巧、踩坑分享 |

### 中文资料

| 资源 | 链接 | 说明 |
|------|------|------|
| AI 编程实战三卷书 | [book.aibuzhiyu.com](https://book.aibuzhiyu.com) | 中文，研发场景 AI 协作方法论体系 |

### 软件工程视角

| 资源 | 链接 | 说明 |
|------|------|------|
| Martin Fowler: Exploring GenAI | [martinfowler.com](https://martinfowler.com/articles/exploring-gen-ai.html) | 软件工程视角的 AI 协作框架 |

---

## 个人学习路径建议

建议按以下顺序深入，每周一个主题：

| 周次 | 主题 | 产出 |
|------|------|------|
| 第 1 周 | Claude Code 官方文档（overview + settings + hooks） | 优化个人 settings.json |
| 第 2 周 | Anthropic Prompt Engineering Guide | 建立个人 Prompt 模板库 |
| 第 3 周 | MCP 协议 + 接入一个内部工具 | 配置一个可用的 MCP Server |
| 第 4 周 | 优化现有项目的 CLAUDE.md | 团队级项目配置文件 v1.0 |

---

## 附录：课件内容对照

以下对照表用于将本大纲与现有课件 `prompting提示词工程-train.md` 关联，方便学习时定位具体内容。

### 第一期 · 课件已有内容

| 课件原文位置 | 课件内容 | 大纲对应位置 | 说明 |
|-------------|---------|-------------|------|
| `## 1. 开场`（7min） | 对比演示 + 研发优势 + 今日目标 | `第一期 · 开场`（5min） | 大纲压缩了，增加了"两期规划" |
| `## 2. 核心原则`（13min） | 5 条铁律 + 正反例 + lexyAdmin 案例 | `第一期 · 5 条铁律`（10min） | 核心内容一致，大纲时间压缩 |
| `## 3. 四种模式` + 四大场景（20min） | 四种模板 + 生成代码/理解代码/调试/Review 详细 Demo | `第一期 · 四种模式`（8min） + `实战`（6min） | 课件中的场景 Demo 被压缩，融入实战环节 |
| `## 4. Q&A`（5min） | 常见问题 + 一句话总结 | `第一期 · Q&A + 第二期引子`（5min） | 增加了"课后作业"和"引子" |

### 第一期 · 课件没有、大纲新增的内容

| 大纲模块 | 课件中对应位置 | 说明 |
|---------|--------------|------|
| **Prompt 模板参数化**（7min） | 无 | 全新内容，需要另外补充 |
| **项目配置文件入门**（4min） | 无（附录B有零散提及） | `CLAUDE.md` 基础结构，附录B的上下文管理速查表有关联 |
| **实战：学员案例改写**（6min） | 无 | 全新互动环节，课件只有讲师单向 Demo |

### 第二期 · 全部来自附录B的进阶速查

| 大纲模块 | 课件原文位置 | 说明 |
|---------|-------------|------|
| **多轮对话状态管理**（12min） | `附录B · 上下文管理速成` | 从速查表扩展为完整模块 |
| **大型代码库导航**（10min） | `附录B · 上下文管理` + `需求拆解` | 分散在附录B两处，大纲整合为独立模块 |
| **AI 辅助 TDD**（10min） | 无 | 全新内容，课件完全没有涉及 |
| **Claude Code 深度工作流**（8min） | 无 | 全新内容，含 MCP、settings.json、高级命令 |

### 速查：我想学什么，去哪里找

| 你想学什么 | 去哪里找 |
|-----------|---------|
| Prompt 写法的基础正反例 | 课件 `## 2. 核心原则` |
| 四种模式的标准模板 | 课件 `## 3. 四种模式` 前半段 |
| 生成代码 / 调试 / Review 的场景 Demo | 课件 `## 3.` 的四个场景小节 |
| 怎么把 prompt 做成可复用模板 | 大纲新增，课件没有 |
| CLAUDE.md 怎么写 | 大纲新增，课件没有 |
| 多轮协作、上下文管理 | 课件 `附录B`（速查级别），大纲第二期展开 |
| 需求拆解方法 | 课件 `附录B · 需求拆解速成` |
| AI 辅助测试 | 大纲新增，课件没有 |

---

## 设计方法与模式：传统原理 vs AI 辅助

> 以下仅涉及**原理层面**的了解，无需深入实践。重点是理解"传统怎么做"与"有了 AI 后怎么变"。

---

### 1. TDD（Test-Driven Development）测试驱动开发

#### 传统原理

经典的**红-绿-重构**循环：

1. **红**：先写一个会失败的测试（定义期望行为）
2. **绿**：写最少代码让测试通过（快速实现）
3. **重构**：优化代码结构，保持测试通过（改进设计）

核心信念：测试先于实现，用测试驱动设计决策。

#### AI 辅助后的变化

| 环节 | 传统做法 | AI 辅助后 |
|------|---------|----------|
| **写测试** | 人写，容易遗漏边界 | AI 根据需求生成测试，**自动覆盖边界、异常、空值** |
| **写实现** | 人根据测试写代码 | AI 根据失败测试直接生成实现代码 |
| **重构** | 人手动调整，风险自担 | AI 在保持测试通过的前提下自动重构，人只需 Review |
| **覆盖率** | 依赖人的经验判断 | AI 可分析未覆盖分支，主动提示补测 |

**本质区别**：传统 TDD 是"人用测试约束自己"，AI 辅助 TDD 是"人用测试约束 AI"。测试从"自我约束工具"变成"人机协作契约"。

---

### 2. Spec / BDD（Behavior-Driven Development）行为驱动开发

#### 传统原理

用**具体的业务示例**描述需求，格式通常为 Given-When-Then：

```
Given 用户已登录
When 点击"下单"按钮
Then 订单状态变为"待支付"
And 库存减少 1 件
```

核心信念：业务、开发、测试三方用**统一的自然语言**描述需求，消除理解偏差。

#### AI 辅助后的变化

| 环节 | 传统做法 | AI 辅助后 |
|------|---------|----------|
| **需求转 Spec** | 三方开会，人工编写 GWT | AI 从 PRD/用户故事直接提取并生成 GWT 格式 |
| **Spec 转测试** | 人手动把 GWT 转成测试代码 | AI 直接把 GWT 翻译成可执行测试 |
| **需求变更** | 手动同步文档、Spec、测试 | AI 识别需求改动，**自动建议**需要更新的 Spec 和测试 |
| **验收** | 业务方读 GWT 文档确认 | AI 用自然语言汇报测试结果，业务方可直接理解 |

**本质区别**：传统 BDD 的核心成本是"翻译"（业务语言 → GWT → 测试代码），AI 大幅压缩了翻译链条，三方可以直接用自然语言协作。

---

### 3. DDD（Domain-Driven Design）领域驱动设计

#### 传统原理

解决**复杂业务领域**的设计方法，核心概念：

- **统一语言（Ubiquitous Language）**：业务、开发用同一套术语
- **限界上下文（Bounded Context）**：大系统拆分为独立业务边界
- **实体 / 值对象 / 聚合根**：领域对象的分类建模
- **领域事件**：业务状态的变更通知

核心信念：代码结构应反映业务领域的真实结构。

#### AI 辅助后的变化

| 环节 | 传统做法 | AI 辅助后 |
|------|---------|----------|
| **提取领域概念** | 人工阅读业务文档，开会讨论 | AI 从需求文档中**自动提取名词、动词、规则**，建议领域模型 |
| **统一语言维护** | 靠人工文档约束，易漂移 | AI 维护词汇表，**自动检查代码命名与业务术语是否一致** |
| **限界上下文划分** | 依赖架构师经验判断 | AI 分析模块依赖关系，建议合理的上下文边界 |
| **领域模型可视化** | 人画 UML/领域图 | AI 根据代码直接生成并维护领域模型图 |
| **战术模式选择** | 人决定用实体还是值对象 | AI 根据业务特征建议合适的 DDD 战术模式 |

**本质区别**：传统 DDD 是"人理解业务后建模"，AI 辅助 DDD 是"AI 辅助人理解业务并共同建模"。AI 降低了 DDD 的**认知门槛和文档维护成本**。

---

### 4. 其它主流设计模式（概览）

#### GoF 设计模式（23 种）

| 类型 | 代表模式 | 传统用途 | AI 辅助后 |
|------|---------|---------|----------|
| 创建型 | 工厂、单例、建造者 | 封装对象创建逻辑 | AI 可识别创建逻辑模式，自动生成或建议 |
| 结构型 | 适配器、装饰器、代理 | 组合对象结构 | AI 识别结构耦合，建议模式解耦 |
| 行为型 | 策略、观察者、命令 | 封装行为变化 | AI 从代码中识别行为变化点，建议引入模式 |

**变化**：传统靠人背诵模式并判断何时使用，AI 可以**识别代码坏味道，主动推荐适用模式**。

#### 架构模式

| 模式 | 传统核心 | AI 辅助后 |
|------|---------|----------|
| **MVC/MVVM** | 分离视图与业务 | AI 自动生成符合分层的代码骨架 |
| **微服务** | 按业务能力拆分 | AI 分析代码依赖，建议合理的拆分边界 |
| **六边形架构** | 核心业务独立于外部 | AI 识别耦合点，建议端口/适配器划分 |
| **Clean Architecture** | 依赖关系向内指向核心 | AI 检查依赖方向，阻止违反分层规则 |

**变化**：传统架构靠架构师经验，AI 可以**自动检查架构约束、建议改进方向**。

---

## 学习资料：设计方法与模式

### TDD

| 资源 | 链接 | 说明 |
|------|------|------|
| Kent Beck《Test-Driven Development》 | 书籍 | TDD 鼻祖，红-绿-重构的经典阐述 |
| Martin Fowler: TDD | [martinfowler.com](https://martinfowler.com/bliki/TestDrivenDevelopment.html) | 软件工程大师的简明解释 |
| xUnit Test Patterns | 书籍 | 测试代码的模式与反模式 |

### BDD / Spec

| 资源 | 链接 | 说明 |
|------|------|------|
| Cucumber BDD 指南 | [cucumber.io](https://cucumber.io/docs/bdd/) | BDD 官方教程，含 Given-When-Then 详解 |
| Gherkin 语法 | [cucumber.io](https://cucumber.io/docs/gherkin/) | Spec 的标准格式规范 |
| Gojko Adzic《Specification by Example》 | 书籍 | 实例化需求的权威著作 |

### DDD

| 资源 | 链接 | 说明 |
|------|------|------|
| Eric Evans《Domain-Driven Design》 | 书籍 | DDD 开山之作，战略+战术设计 |
| Vaughn Vernon《Implementing DDD》 | 书籍 | DDD 落地实践指南 |
| DDD Community | [dddcommunity.org](https://dddcommunity.org) | 官方社区，含模式目录 |
| Martin Fowler: DDD 概述 | [martinfowler.com](https://martinfowler.com/tags/domain%20driven%20design.html) | 快速建立概念框架 |

### 设计模式

| 资源 | 链接 | 说明 |
|------|------|------|
| Refactoring.Guru 设计模式 | [refactoring.guru](https://refactoring.guru/design-patterns) | 可视化 + 代码示例，最易懂的入门 |
| GoF《Design Patterns》 | 书籍 | 经典原著，23 种模式定义 |
| SourceMaking | [sourcemaking.com](https://sourcemaking.com/design_patterns) | 模式 + 反模式 + UML 图 |

### 架构

| 资源 | 链接 | 说明 |
|------|------|------|
| Clean Architecture (Uncle Bob) | [blog.cleancoder.com](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) | 整洁架构原文 |
| Martin Fowler: Microservices | [martinfowler.com](https://martinfowler.com/articles/microservices.html) | 微服务定义文章 |
| Hexagonal Architecture | [alistair.cockburn.us](https://alistair.cockburn.us/hexagonal-architecture/) | 六边形架构原文 |

### AI 辅助编程（原理视角）

| 资源 | 链接 | 说明 |
|------|------|------|
| Anthropic: AI-assisted testing | [Cookbook 测试示例](https://github.com/anthropics/anthropic-cookbook) | 官方代码库中的测试相关示例 |
| AI 编程实战三卷书 | [book.aibuzhiyu.com](https://book.aibuzhiyu.com) | 中文，含 AI 辅助设计方法论的章节 |
| Simon Willison: AI-assisted coding | [simonwillison.net](https://simonwillison.net/tags/ai-assisted-coding/) | 长期跟踪 AI 编程实践的开发者博客 |

---

## 一张图总结：传统 vs AI 辅助

```
传统软件开发          AI 辅助软件开发
    │                      │
    ▼                      ▼
人理解需求 ───────→  AI 辅助提取需求 + 人确认
    │                      │
    ▼                      ▼
人设计架构/模式 ──→  AI 建议架构 + 人决策
    │                      │
    ▼                      ▼
人写测试 ─────────→  AI 生成测试（含边界）+ 人 Review
    │                      │
    ▼                      ▼
人写实现 ─────────→  AI 生成实现 + 人验证
    │                      │
    ▼                      ▼
人重构优化 ───────→  AI 自动重构 + 人确认
    │                      │
    ▼                      ▼
人维护文档 ───────→  AI 同步维护文档 + 人抽查
```

**核心变化**：AI 不是替代人的决策，而是把人的角色从"亲自做每一步"变成"定义标准 + 审查结果"。

---

*创建时间：2026-05-25*
