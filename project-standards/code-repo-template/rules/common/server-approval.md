# 服务器变更审批

对 {{SERVER_ALIAS_1}}（{{SERVER_IP_1}}）或 {{SERVER_ALIAS_2}}（{{SERVER_IP_2}}）执行操作的边界：

## ✅ 只读操作 — 无需确认，直接执行

- MySQL `SELECT` / `SHOW` / `DESC` / `EXPLAIN`
- Redis `GET` / `KEYS` / `TYPE` / `TTL` / `LRANGE` / `HGETALL` / `SCAN` / `INFO` 等只读命令
- 文件只读：`cat` / `tail` / `less` / `grep` / `ls` / `ps` / `df` / `free` / `journalctl`（不带 `--vacuum`）
- `systemctl status` / `docker ps` / `docker logs`

## ⛔ 写入操作 — 必须先询问，提供完整命令让用户选「自己执行/帮我执行」

- MySQL `INSERT` / `UPDATE` / `DELETE` / `ALTER` / `DROP` / `TRUNCATE` / `CREATE`
- Redis `SET` / `DEL` / `FLUSHDB` / `FLUSHALL` / `CONFIG SET` / `EXPIRE`
- 文件写入：`vim` 保存、`>` / `>>` 重定向、`rm` / `mv` / `chmod` / `chown`
- 服务变更：`systemctl restart|stop|start|reload` / `docker restart|rm` / 代码部署 / 环境变量改动
- 任何 `sudo` 写入类操作

## 询问话术格式

```
需要修改 {{SERVER_ALIAS_1}} 的 Redis 配置，具体命令：

ssh {{SERVER_ALIAS_1}}
vim /etc/redis/redis.conf
# 修改 maxmemory 512mb
systemctl restart redis

请选择：
1. 我自己执行
2. 帮我执行
```

## 凭证边界

- 远程数据库/Redis 凭证只能从服务器上获取，不可写入项目文件
- 本地是否允许直连远程 DB/Redis，按项目 CLAUDE.md 附加红线约定；未约定时默认禁止直连
