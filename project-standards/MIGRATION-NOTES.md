# MIGRATION-NOTES — 迁移说明与来源映射

> 记录模板包从 workspace / token-docs / token-hub 三级规则体系提炼时的定稿决策、每个文件的来源与脱敏动作。规格：`../02-specs/project-standards-template-spec-20260718.md`（v9）。

## 一、冲突定稿四项（以规格 §2 为准）

| # | 冲突 | 定稿 | 依据 |
|---|------|------|------|
| A1 | 分支命名两套规范并存（spec 联动式 vs 语义式） | spec 联动式 `feature/YYYYMMDD_spec_<规格标识>` 为主；无 spec 杂项用 `chore\|fix/<简述>` 兜底 | spec 联动保证 git log 可追溯需求来源，与「代码与文档同包提交」原则闭环 |
| B1 | 并行 Agent 数两处矛盾（≤2 vs ≤3） | 占位符 `{{MAX_PARALLEL_AGENTS}}`，默认 2 | 机器承载力因人而异，参数化消灭矛盾源 |
| B2 | 流程图「5角色」vs 表格 9 角色 | 统一 9 角色，流程图同步改写 | 表格为准（含法律合规等后补角色） |
| B6 | WSL 测试命令两版不一致（命令与归因都不同） | 合并版：`MSYS_NO_PATHCONV=1 wsl -e bash -c '… CGO_ENABLED=1 …'`，归因写全（CGO + 文件锁双原因） | 两个失败原因独立存在，缺一个归因都会误导排查 |

## 二、来源映射表（43 文件）

### 包根（2）

| 源 | 模板文件 | 动作 |
|----|---------|------|
| 新写 | → `README.md` | 包定位 / 启用清单 / 占位符总表 / 版本锚与变更记录 |
| 新写 | → `MIGRATION-NOTES.md` | 本文件 |

### docs-repo-template（19）

| 源 | 模板文件 | 动作 |
|----|---------|------|
| token-docs `README.md` | → `README.md` | 保留目录说明/命名规范/流转规则；删除分支合并记录、汇总表、工具节；项目名 → `{{PROJECT_NAME}}` |
| 新写 | → `.gitignore` | 凭据/本地文件/临时文件三类忽略 |
| 新写 | → `credentials.local.md.example` | 警示头 + 占位符映射表 |
| token-docs `00-taskregister/_TEMPLATE.md` | → `00-taskregister/_TEMPLATE.md` | 原样复制，状态行补 ❌（对齐五状态） |
| 新写 | → `00-taskregister/taskregister-index.md` | 活跃总表 + 归档两节骨架 |
| 新写 | → `01-requirements/.gitkeep` | 空目录占位 |
| 新写 | → `06-database/.gitkeep` | 空目录占位 |
| 新写 | → `07-process/.gitkeep` | 空目录占位 |
| 新写 | → `09-reports/.gitkeep` | 空目录占位 |
| 新写 | → `11-manuals/.gitkeep` | 空目录占位 |
| 新写 | → `12-resources/.gitkeep` | 空目录占位 |
| 新写 | → `02-specs/_TEMPLATE-spec.md` | §5 验收标准（验证方式列）+ §6 人工测试清单 + EARS 示例 + 范围外 |
| 新写（结构对齐 stack-go/api.md + stack-go/error.md） | → `03-design/api-spec.md` | 版本号头 + 统一响应/分页/错误格式 + 错误码规则与分段表 + 空码表 + 接口骨架（唯一事实源） |
| 新写 | → `04-plans/_TEMPLATE-plan.md` | Phase/T 编号 + 自动验收命令字段 + E2E 节默认引用冒烟脚本 |
| 新写 | → `05-tasklist/todo.md` | 单一结构总索引 |
| 新写 | → `05-tasklist/_TEMPLATE-todo.md` | 纯状态索引（T 编号+状态+plan 锚点，禁止复制验收细节） |
| 新写 | → `08-test/_TEMPLATE-smoke-test.sh` | 健康检查 + 核心链路占位 + 非零退出码 |
| 新写 | → `10-deployment/_TEMPLATE-deploy-checklist.md` | 三段交接：编码自检 → 人工终测（门禁④）→ 部署审批（门禁4） |

### code-repo-template（23）

| 源 | 模板文件 | 动作 |
|----|---------|------|
| token-hub `CLAUDE.md` 核心规则精选 | → `CLAUDE.md.template` | 压缩为四块薄入口（定位/Top 红线/命令速查/指针），全量规则条款移入 rules/ |
| 新写 | → `AGENTS.md.template` | 薄引用，`@rules/rules-index.md` 语法 |
| 新写 | → `.gitignore` | `.env*`/`*.local.*`/日志/二进制/coverage 出厂卫生 |
| 新写 | → `.claude/settings.json.template` | allow/deny/hooks（映射见下节） |
| 新写 | → `.claude/hooks/guard-hard-interrupt.sh` | 3 类机器识别硬中断拦截，POSIX sh |
| workspace `.githooks/` 先例 | → `.githooks/commit-msg` | 新写脚本，校验 `<type>(<scope>): <subject>` |
| token-hub `CLAUDE.md` 按需加载表 | → `rules/rules-index.md` | 重组为触发表 + 新栈三步协议 + common 不变承诺 + 优先级声明 |
| workspace `CLAUDE.md` 任务工作流节 | → `rules/common/workflow.md` | 9 角色统一（B2）、并行 → `{{MAX_PARALLEL_AGENTS}}`（B1）、命令 → 占位符、新增执行模式两挡协议 |
| workspace 对话规范 + token-hub 补充条款 | → `rules/common/conversation.md` | 六条款合并（一次一问/停问/带方案/禁替选/一次失败即问/Bug 逐个验收） |
| token-hub 分支+提交规范 + workspace 代码更新规则 | → `rules/common/git.md` | A1 定稿命名、`master` → `{{MAIN_BRANCH}}`、type 列表与 commit-msg hook 对齐、fetch 五步协议 |
| token-docs README 流转规则 + token-hub 归档/落盘/待办条款 | → `rules/common/docs-flow.md` | 双仓分层 + `_archived-` 归档 + 待办必问登记 |
| token-hub `.trae/rules/rules_api_integration.md` | → `rules/common/api-contract.md` | 保留契约流程/微调 vs breaking/8 项核对清单/版本号规则；删除 httptest、PR 模板、页面清单等实现细节（语言无关化） |
| workspace/token-hub 服务器变更审批节 | → `rules/common/server-approval.md` | 服务器别名/IP → `{{SERVER_ALIAS_n}}`/`{{SERVER_IP_n}}`；本地直连边界改为按项目红线约定 |
| `.trae/rules/rules_arch.md` | → `rules/stack-go/arch.md` | 原样迁移 |
| `.trae/rules/rules_error.md` | → `rules/stack-go/error.md` | 补「严禁打日志然后丢弃」红线；码表链接改文档仓路径；补「存量修复一处一改」 |
| `.trae/rules/rules_logging.md` | → `rules/stack-go/logging.md` | 凭证 Header 红线泛化（去厂商专名，改「各厂商 api-key 变体」）；去日期戳 |
| `.trae/rules/rules_database.md` | → `rules/stack-go/database.md` | 原样迁移 + 补「每个 migration 必须有回滚方案」；DSN 描述去项目专属函数名 |
| `.trae/rules/rules_redis.md` | → `rules/stack-go/redis.md` | DB0~DB6 业务分配表 → 「按业务域分逻辑 DB」方法论 + 两行示例；去历史 key 白名单 |
| `.trae/rules/rules_api.md` | → `rules/stack-go/api.md` | 原样迁移 |
| `.trae/rules/rules_testing.md` | → `rules/stack-go/testing.md` | B6 合并版命令、路径 → `{{PROJECT_PATH}}`、归因写全（CGO+文件锁）；去 WSL 发行版/版本专属描述 |
| `.trae/rules/rules_ops.md` | → `rules/stack-go/ops.md` | 原样迁移（上游 API → 上游依赖） |
| token-hub `CLAUDE.md` 全局硬约束 + 服务重启三步 + 避免重复下载 | → `rules/stack-go/build.md` | Go 版本 → `{{GO_VERSION}}`、二进制名 → `{{PROJECT_NAME}}.exe`、健康检查 → `{{HEALTH_URL}}` |
| 9 角色表前端两行 + token-hub 业务约束 | → `rules/stack-vue3/frontend-core.md` | 反向生成条款；项目特有红线不进模板（见下节示例） |

## 三、settings.json / hook 与文档规则映射

| 执行层配置 | 对应文档规则 | 分层说明 |
|-----------|-------------|---------|
| allow：`{{TEST_CMD}}` / `{{BUILD_CMD}}` / `{{LINT_CMD}}` | `common/server-approval.md` 只读直接执行原则 + `workflow.md` 自动挡运行规则 | 自动挡不弹确认窗的前提 |
| allow：只读 git（status/diff/log/fetch/branch） | `common/git.md` fetch 协议 | 查询类放行 |
| deny：`docker push/rm/restart`、`scp`、`rsync` | `workflow.md` 硬中断红线 ②部署动作 | 静态兜底 |
| deny：`git push --force/-f`、`git reset --hard`、`git branch -D` | `workflow.md` 硬中断红线 ③破坏性 git | 静态兜底 |
| deny：`rm -rf` | 通用防误删 | 静态兜底 |
| hook 拦截：ssh 写模式 | `common/server-approval.md` 写入审批（ssh 不进静态 deny——只读 ssh 需放行，写入 ssh 动态判别） | 动态拦截 + 审批话术 |
| hook 拦截：部署/破坏性 git 模式 | `workflow.md` 硬中断红线 ②③ | 与 deny 双层防护（hook 带话术，deny 兜底） |
| `.githooks/commit-msg` | `common/git.md` 提交信息格式 | git 层事中校验（约束人与 AI 的所有提交）；settings 管 AI 命令执行权限（事前），互补不互替 |

第 4 类硬中断「spec 内部矛盾 / 验收标准不可自动判定」属认知判断，由 `workflow.md` 条款约束 AI 自停，执行层不覆盖。

## 四、项目自定义示例（这类内容不进模板正文）

**① 项目自定义红线**（加在项目 `CLAUDE.md` 的 Top 红线块，优先级最高）：

> 例：某行情类项目的「红涨绿跌（`--color-up: #f56c6c`）」「价格必须用 `formatPrice()`」——这是业务域约束，不是 Vue3 通用规范，因此不写入 `stack-vue3/frontend-core.md`（该文件只保留「金额展示用统一格式化函数」的通用条款），具体色值与函数名由项目 CLAUDE.md 附加。

**② 项目自定义角色体系**：

> 例：token-hub 的 `/1~/8` 行业专家角色（产品/项管/架构/开发/测试/运维/DBA/运营，绑定行业标杆项目对比）——属项目自定义评审工具，不进 `common/workflow.md` 的 9 角色门禁体系；需要时在项目 CLAUDE.md 中自行定义并与 9 角色并存（9 角色管门禁，专家角色管日常讨论）。

## 五、旧版 Trae 兜底写法（模板不出厂，需要时手工添加）

新版 Trae 全家桶已原生支持 AGENTS.md（CLI 始终自动加载；Work 桌面版开导入开关），模板因此不出厂 `.trae/`。仅当使用**旧版 Trae IDE**（只认 `.trae/rules/`）时，手工添加 `.trae/rules/ref.md`：

```markdown
---
alwaysApply: true
---

规则单一事实源：`../../rules/`，总索引 `../../rules/rules-index.md`。本文件仅为旧版 Trae 兼容指针，不承载规则条款。
```

**⚠️ frontmatter 必须写 `alwaysApply: true`**——Trae 规则文件无 frontmatter 时按「手动调用模式」处理，裸 Markdown 不会自动加载（哑弹）。
