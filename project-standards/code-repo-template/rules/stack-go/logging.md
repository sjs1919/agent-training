# 日志规则

## 级别

- Debug(调试) | Info(关键流程) | Warn(预期内异常) | Error(非预期错误) | Fatal(不可恢复，进程退出)

## 必选字段

- 每条日志必须含 `trace_id` + `caller`（行号）+ `func_io`（出入参）

## 敏感信息

- 密钥/密码完全不输出，Token 用统一脱敏函数处理后再落日志

## 凭证 Header 红线（强制）

上游/第三方 API 凭证是核心资产，**禁止以任何形式落入日志、错误信息、metrics、trace、监控面板**：

| 禁止落入日志的字段（请求/响应/转发链路全程） |
|---|
| `Authorization`（含 `Bearer xxx` / `Basic xxx`） |
| 认证类自定义 Header（`x-api-key` 及各厂商 api-key 变体） |
| 上游 `provider_key` / 第三方密钥任何明文或片段 |
| 本服务自身 JWT 的完整 token 字符串 |
| 注册/登录请求中的 `password` / `confirm_password` 明文字段 |

### 落地要求

- `func_io` 中间件记录 request/response header 时，**必须过滤**上述字段。用统一 deny list 而非各处散落判断
- 转发上游时，**禁止把上游密钥拼接到 `fmt.Errorf` / 日志 message 中**（哪怕带「调试」目的）
- 错误信息（含 sentinel error 的 Message 字段）禁止包含上述字段任何明文/片段
- SSE 流日志必须先剥离这些 header 再记录
- 测试用例中如出现真实 token，提交前必须脱敏或改 placeholder
- 排查 bug 临时打开调试日志 → 解决后立即关闭，**禁止把调试日志留到发布分支**

### 检测手段

- code review 必查：grep `Authorization|x-api-key|provider_key` 在日志/错误构造/响应输出附近的所有出现
- 上线前 grep 全部日志输出（`tail -1000 logs/server.log | grep -Ei 'sk-[a-z0-9]{20,}|Bearer\s+[a-z0-9]{20,}'`），必须无命中

## 语言

- 生产日志/错误信息统一使用中文，便于国内团队检索排查
- 专有名词保留英文（如 trace_id、func_io、sse_stream 等字段名）

## 格式

- 消息小写开头，不加句号

## 请求出入参（禁止截断）

- 所有请求通过 `func_io` 完整记录出入参
- GET 读 URL query string，POST/PUT/DELETE 读 request body
- 健康检查（`/health`、`/ready`）仅记录基础字段，不记录出入参
- 请求体读取后必须通过 `io.NopCloser(bytes.NewBuffer(bodyBytes))` 恢复 Body
- 响应体通过 responseBodyWriter 捕获，必须实现 `http.Flusher` 接口

## SSE 流式日志

- 出参记录流摘要：`{"type":"sse_stream","total_chunks":N,"duration_ms":M}`
- 逐 chunk 记录：`sse chunk in`（Debug/上游原始）+ `sse chunk out`（Debug/转换后输出）
- `chunk_data` 解析为 JSON 对象，解析失败回退原始字符串，禁止截断
- 流开始：`sse request`（Info 级摘要）+ `sse body`（Debug 级完整请求体）
- 流结束：`sse stream ended`（Info 级，含 `total_chunks` + `duration_ms`）

## 调用规范

- 统一用 `logger.Info()`/`Warn()`/`Error()`/`Debug()`/`Fatal()` 快捷方法
- 禁止绕过封装直接取底层实例调用（否则 caller 行号错位）
