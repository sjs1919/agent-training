#!/bin/sh
# 冒烟测试骨架：任何一步失败即非零退出（自动挡门禁2的机器判定入口）
set -e
BASE="{{HEALTH_URL}}"
echo "[1/2] 健康检查 $BASE"
code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE")
[ "$code" = "200" ] || { echo "SMOKE FAIL: health=$code"; exit 1; }
echo "[2/2] 核心链路（按项目补充，双栈按 {{TEST_CMD_GO}}/{{TEST_CMD_WEB}} 分段）"
# 示例：curl -s -X POST "$API/v1/xxx" -d '{}' | grep -q '"code":200' || { echo "SMOKE FAIL: xxx"; exit 1; }
echo "SMOKE PASS"
