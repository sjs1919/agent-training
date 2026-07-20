# 项目规范模板包

`TEMPLATE_VERSION: 1.0`

新项目开箱即用的「双仓 + 规则 + 四门禁自动挡」体系：复制两个子模板 + 替换占位符，即可运转 spec → plan → todo → 四门禁全流程。

## 包定位（三层概念 → 物理结构）

| 概念层 | 物理位置 | 内容 |
|--------|---------|------|
| 通用协作层（语言无关） | `code-repo-template/rules/common/` | 工作流四门禁+两挡、对话规范、测试、部署、Git、文档流转、API 契约、服务器审批、技能集成（9 文件） |
| 技术栈层（可插拔） | `code-repo-template/rules/stack-go/`、`stack-vue3/` | Go 9 文件 + Vue3 1 文件；新栈按「三步追加协议」扩展，common 永不改 |
| 基础设施层（模板+骨架+执行层） | `docs-repo-template/` + `code-repo-template/`（入口与 `.claude/`、`.githooks/`） | 文档仓 13 目录骨架与流程模板；薄入口 CLAUDE/AGENTS、权限白名单、拦截 hook、提交校验 |

## 模板变更记录

### [1.0] - 2026-07-19

#### Added

- 首版：双仓模板 + rules 三层（common 6 / stack-go 9 / stack-vue3 1）+ 执行层（settings.json 模板 / guard hook / commit-msg / 冒烟脚本骨架）

### [1.1] - 2026-07-20

#### Added

- 技能集成：`rules/common/skill-integration.md` — Superpowers-zh Brainstorming、CodeGraph、Understand-Anything 三 Skill 与工作流的联动规范
- workflow.md：新增阶段1「需求变更影响分析」、阶段0 UI 原型设计指引、门禁引用
- rules-index.md：新增 skill-integration 两条触发器（需求澄清 + 需求变更影响分析）

> 约定：模板改进只回填本模板包并在此记一行变更（Added / Changed / Fixed 三类）；已复制的项目对照变更记录按需升级，防模板自身漂移。

## 新项目启用清单

1. 复制 `docs-repo-template/` → 新建 `<project>-docs` 文档仓
2. 复制 `code-repo-template/` 全部内容 → 新项目代码仓根目录
3. **全局替换占位符**（表见下节；技术栈类占位符按项目命令填写）
4. 删除不用的 `rules/stack-*/` 目录，并同步删除 `rules/rules-index.md` 中对应触发行
5. 三个 `.template` 去后缀启用：`CLAUDE.md.template` → `CLAUDE.md`、`AGENTS.md.template` → `AGENTS.md`、`.claude/settings.json.template` → `.claude/settings.json`
6. **Trae Work 桌面版用户**：设置 > 规则 > 导入设置，打开「将 AGENTS.md / CLAUDE.md 包含在上下文中」开关（**非默认开启**；Trae CLI 无需此步，AGENTS.md 始终自动加载）
7. hook 赋权：`chmod +x .claude/hooks/guard-hard-interrupt.sh .githooks/commit-msg`
8. 启用 git hooks：`git config core.hooksPath .githooks`
9. 文档仓：复制 `credentials.local.md.example` → `credentials.local.md`，填入真实值（该文件已被 .gitignore 忽略）
10. **启用自检（四项全部符合预期才算启用完成）**：
    1. 让 AI 执行 `git push --force` 样例 → 确认被 hook 拦截（阻断 + 审批提示）
    2. 让 AI 跑 `{{TEST_CMD}}` → 确认放行、不弹确认窗
    3. 提交一条非法格式 message（如 `update stuff`）→ 确认被 commit-msg 拒绝
    4. 问 AI「当前项目规则是什么」→ 确认能列出 `rules/rules-index.md` 触发表（规则已加载）

## 外部 Skill 依赖（可选）

项目可选的三个外部 Skill，按需安装，非强制依赖。

| Skill | 安装方式 | 首次使用前必须 |
|-------|---------|---------------|
| Superpowers-zh | `npx superpowers-zh`（项目级安装） | 确认 `using-superpowers` bootstrap 已加载 |
| CodeGraph | `npx @mschreib28/codegraph` + `codegraph init -i` | 构建语义图谱索引（`.codegraph/`） |
| Understand-Anything | 由 registry 安装 | 跑一次 `/understand` 构建交互图谱（`.understand-anything/` 可提交 Git） |

详细使用方式见 `rules/common/skill-integration.md`。

## 占位符总表

| 占位符 | 含义 | 示例 |
|--------|------|------|
| `{{PROJECT_NAME}}` | 项目名 | my-service |
| `{{PROJECT_DESC}}` | 一句话定位 | 某某 API 网关 |
| `{{DOCS_REPO}}` | 文档仓路径/地址 | ../my-service-docs |
| `{{MAIN_BRANCH}}` | 生产分支名 | master |
| `{{GIT_PLATFORM}}` | Git 平台 | Gitee |
| `{{GO_VERSION}}` | Go 版本约束 | 1.21 |
| `{{TEST_CMD}}` | 测试命令 | go test ./internal/... |
| `{{BUILD_CMD}}` | 构建命令 | go build ./cmd/ |
| `{{LINT_CMD}}` | 静态检查命令 | go vet ./internal/... |
| `{{PROJECT_PATH}}` | WSL 内项目路径 | /mnt/c/workspace/projects/my-service |
| `{{HEALTH_URL}}` | 服务健康检查地址（冒烟脚本用） | http://localhost:8080/health |
| `{{MAX_PARALLEL_AGENTS}}` | 并行 Agent 上限 | 2 |
| `{{SERVER_ALIAS_n}}` / `{{SERVER_IP_n}}` | 服务器别名/IP 对（n=1,2…） | srv_prod / x.x.x.x |

**双栈约定**：多技术栈项目的命令类占位符按 stack 拆分——推荐 `{{TEST_CMD_GO}}` / `{{TEST_CMD_WEB}}`、`{{BUILD_CMD_GO}}` / `{{BUILD_CMD_WEB}}`（冒烟脚本与 settings.json allow 分段引用）；简单场景可用 `&&` 串联单占位符。

**凭据类占位符（不做全局替换）**：`{{DB_PASSWORD}}`、`{{JWT_SECRET}}`、`{{SMTP_AUTH_CODE}}` 等仅存在于 `credentials.local.md(.example)` 映射表中，按项目增删行；文档/代码中永远保留占位符形态，真实值只写入被 gitignore 的 `credentials.local.md`。

## 兜底与升级

- 模板文件的改进**只回填本模板包**（并在「模板变更记录」记一行），不直接改已复制项目——已复制项目对照变更记录自行升级
- 项目 `CLAUDE.md` 的「基于模板 vX.Y」字段用于识别项目所用模板版本
- 旧版 Trae IDE（仅支持 `.trae/rules/`）的兜底写法见 `MIGRATION-NOTES.md`
