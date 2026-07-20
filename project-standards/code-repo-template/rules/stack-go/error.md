# 错误处理与错误码规则

## 错误处理

- 所有 `error` 必须检查，禁止 `_` 忽略（除非确定不出错且加注释说明）
- 错误包装用 `%w`（保留错误链），不用 `%v`
- 业务错误用 sentinel error（`var ErrXxx = errors.New()`）+ `errors.Is()`/`errors.As()`
- 错误不重复日志：下层记录后抛上层，上层不重复记录（除非补充上下文）
- `panic` 仅限启动阶段不可恢复错误，业务逻辑禁止
- **🚫 严禁「打日志然后丢弃」**：所有 error 必须向上传播（`return fmt.Errorf("操作描述: %w", err)`）
- **关键写操作失败必须向上返回 error**：涉及资金、权限、审计等对账关键路径的写操作，仅日志记录不足以上报故障，必须通过 `return error` 向调用方传播，确保上层感知并执行补偿或告警

## 错误信息语言

- `fmt.Errorf`、`errors.New`、`.WithMessage()` 等错误信息统一使用中文
- 专有名词保留英文（如 mysql、redis、jwt 等技术名词）
- 错误信息格式：`操作描述: %w`（包装错误）或 `操作描述: 具体原因`

## 错误码

- 格式：5 位 = 3 位 HTTP 状态码 + 2 位业务细分码（如 `40001`、`40101`、`40301`）
- **全部集中在 `internal/errcode/errcode.go` 定义，禁止硬编码**
- 每个错误码含 `Code` + `Message`（中文），支持 `WithMessage()` 自定义
- Handler 层统一用 `middleware.Error(c, code, msg)` 返回结构化错误
- **详细码表与分段以文档仓 `03-design/api-spec.md` 为唯一事实源，本规则不重复**

## 错误码使用规范

- 禁止在代码中直接使用 `errors.New("自定义错误")` 或 `fmt.Errorf("自定义错误")` 作为业务错误返回
- 所有业务错误必须通过 `errcode` 包中的预定义错误码，或使用 `WithMessage()` 自定义消息
- 模块内部 sentinel error 仅限模块内分流决策，禁止跨层传播到 Handler
- 新增业务错误码时，必须先更新 `internal/errcode/errcode.go`，再引用使用
- 修复存量错误处理问题时：发现一处修一处，不批量
