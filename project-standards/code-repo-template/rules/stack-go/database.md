# 数据库规则

## 表与字段

- 表名复数小写下划线（`users`、`model_permissions`）
- 时间字段必含 `created_at`/`updated_at`（GORM 自动管理）
- 业务字段设 `gorm:"default:xxx"`；高频查询字段加 `gorm:"index"`，联合唯一用 `uniqueIndex:idx_xxx`
- 敏感字段（密码哈希、Token 哈希）JSON 序列化用 `json:"-"` 隐藏

## 连接

- DSN 从配置文件读取，通过统一配置入口生成，禁止散落硬编码

## 禁止项

- 禁止 AutoMigrate，表结构变更通过 `sql/` 目录下 SQL 迁移脚本管理
- 禁止外键（FOREIGN KEY 和 `gorm:"foreignKey"`/`gorm:"constraint"` 标签），关联由应用层保证

## 索引长度

- utf8mb4 下 VARCHAR 字段 ×4 ≤ 767 字节（如 SHA256 用 `VARCHAR(64)`）

## 迁移脚本

- 命名 `NNN_描述.sql`（如 `001_init.sql`），编号递增不可跳过
- 必须幂等（使用 `IF NOT EXISTS`），头部注释说明里程碑和执行前提
- 每个 migration 必须有回滚方案

## CREATE TABLE 强制规范

- 每句 `CREATE TABLE` 末尾**必须完整写出**三个属性，一个不能少：

  ```sql
  ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  ```

- ❌ 禁止只写 `CHARSET=utf8mb4` 不写 `COLLATE` — 不同 MySQL 服务器默认 COLLATE 不同（8.0 默认 `0900_ai_ci`，旧版/部分云服务默认 `unicode_ci`），导致同一条 SQL 在不同环境跑出不同表结构，JOIN 时报 `Illegal mix of collations`
- ALTER TABLE 新增 VARCHAR 列时也必须显式指定 COLLATE

## 操作确认要求

- **所有数据库写操作（INSERT/UPDATE/DELETE/DROP/TRUNCATE）必须先确认后才能执行**
- 执行前必须告知用户：操作类型、影响范围（表名/预估行数/条件范围）、不可逆性说明
