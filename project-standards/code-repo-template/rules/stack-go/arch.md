# 架构与分层规则

## 三层架构

- Handler（`internal/handler/`）：参数绑定校验 + 调用 Service + 组装响应，不含业务逻辑
- Service（`internal/service/`）：业务逻辑 + 事务编排 + 跨 Repo 协调，不直接操作 DB
- Repository（`internal/repository/`）：CRUD 封装，不含业务判断
- 禁止跨层：Handler 不调 Repository，Service 不返回 HTTP 响应

## DTO/VO 分离

- Request 结构体（含 `binding` 校验标签）定义在 Handler 层
- Response/VO 结构体（过滤敏感字段、格式化输出）定义在 Handler 层
- Model（`internal/model/`）不得直接用于请求绑定或响应序列化
- 转换函数 `toModel()`/`toResponse()` 在 Handler 层完成

## 包与文件

- 每个包职责单一，禁止跨包混杂
- 禁止循环导入，出现时抽离公共接口到独立包
