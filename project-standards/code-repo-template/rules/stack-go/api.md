# API 设计规则

> 响应格式、分页约定、错误码以文档仓 `03-design/api-spec.md` 为唯一事实源，本规则不重复。

## HTTP 语义

- GET 查询/幂等 | POST 创建/非幂等 | PUT 全量更新/幂等 | DELETE 删除/幂等

## URL 与参数

- URL 全小写连字符（`/api/v1/user-tokens`）
- 路径参数 Gin 风格 `/:id`（如 `/api/v1/token/:id/toggle`）

## 参数校验

- 请求结构体必须用 `binding` 标签声明校验规则（`required`/`min`/`max`/`oneof`）
- Handler 层 `ShouldBindJSON()`/`ShouldBindQuery()` 自动校验，失败返 400
