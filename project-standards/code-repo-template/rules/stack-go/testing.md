# 测试规则（Go）

> TDD 流程、三测分层、测什么/不测什么、质量门禁见 `common/testing.md`。本文件仅 Go 专属执行细节。

## 测试环境：WSL（强制）

**Windows 下全量测试必须在 WSL 中执行**，两个独立原因（缺一都会误报）：

1. **CGO**：Windows 环境 `CGO_ENABLED=0`，go-sqlite3 等 CGO 依赖无法工作，相关测试必定失败
2. **文件锁**：Windows 下 SQLite 测试存在 `test.db` 文件锁清理失败问题（Go test 框架 `TempDir RemoveAll` 时报 `The process cannot access the file`），导致大量测试误报 FAIL

```bash
# 在 Windows Git Bash 执行（统一命令）：
MSYS_NO_PATHCONV=1 wsl -e bash -c 'export PATH=/usr/local/go/bin:/usr/bin:/usr/local/bin:/bin:$PATH && cd {{PROJECT_PATH}} && CGO_ENABLED=1 GOPROXY=https://goproxy.cn,direct go test ./internal/... -count=1'
```

> **为什么这样写**：`wsl -e bash -c` 启动非交互式 shell，不加载 profile，PATH 默认不含 `/usr/bin`，必须手动 export；`MSYS_NO_PATHCONV=1` 防止 Git Bash 把路径参数错误转换。WSL 内需预装 Go 与 gcc。

- **Windows 允许仅跑非 CGO 包**（快速反馈，按项目列出包清单）
- **完整回归必须走 WSL**（上方命令）

## 文件与命名

- 测试文件与源文件同目录，命名 `xxx_test.go`
- 函数命名 `TestXxx_场景`（如 `TestCreateToken_Success`、`TestCreateToken_DuplicateHash`）
- Arrange → Act → Assert 三段清晰

## 表驱动

- 多场景测试用 `[]struct{ name string; ... }` 表驱动模式

## Mock

- 依赖外部服务（DB、上游 API）时用接口 + Mock 替代，不依赖真实外部连接
- Mock 文件命名 `xxx_mock.go`，放在同目录

## API 字段对齐测试

- 每个 Handler 必须有 `httptest` 字段对齐测试，对比 `03-design/api-spec.md`
- 通用 checker 放 `tests/testutil/api_spec_checker.go`
- 字段多了/少了/命名错误 → 测试失败 → 当场修复文档或代码

## 执行

- 提交前 `{{TEST_CMD}}` 必须通过，禁止提交失败测试
- 运行测试后必须**阅读输出**确认 PASS 数量，不能只看「没有红色」
