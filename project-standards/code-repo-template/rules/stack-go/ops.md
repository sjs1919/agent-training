# 运维与优雅关闭规则

## 优雅关闭

- 监听 SIGINT/SIGTERM，收到后按序执行：停接新请求 → `http.Server.Shutdown(ctx)` 等进行中请求完成 → 关 DB → 停定时任务 → `WaitGroup.Wait()` 确认 goroutine 退出 → 退出进程
- 总超时 30s，超时后强制退出

## 健康检查

- `/health`（存活检查 liveness）：仅检查进程存活，始终返回 200
- `/ready`（就绪检查 readiness）：检查 DB 连接、上游依赖可达性，任一依赖不可用返 503

## 启动顺序

- 配置加载 → 日志初始化 → DB 连接（失败 panic）→ HTTP 客户端初始化 → 定时任务启动 → HTTP Server 启动

## Context

- I/O 函数首参数 `ctx context.Context`
- `*gin.Context` 仅 Handler 层使用，Service/Repo 用 `c.Request.Context()` 提取
- DB 查询和上游 API 调用必须 `context.WithTimeout()`，超时值从配置读取
- 长时间操作必须尊重 ctx 取消信号（`select { case <-ctx.Done(): }`）
- 后台 goroutine 必须传入可取消 context，禁止 `context.Background()` 启动无法终止的 goroutine
