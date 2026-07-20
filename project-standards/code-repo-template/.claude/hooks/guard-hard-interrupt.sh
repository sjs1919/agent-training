#!/bin/sh
# PreToolUse hook：拦截 3 类可机器识别硬中断（ssh 写 / 部署 / 破坏性 git）
# 第 4 类「spec 矛盾/验收不可判定」属认知判断，由 rules/common/workflow.md 约束 AI 自停
# stdin: {"tool_name":"Bash","tool_input":{"command":"..."}}  exit 0 放行 / exit 2 阻断
# 已知取舍：sed 提取 JSON 对转义引号不严谨、">" 匹配可能误伤引号内字符串——宁可多拦一次问人，不可漏拦；settings.json deny 为静态兜底
input=$(cat)
cmd=$(printf '%s' "$input" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\(.*\)".*/\1/p')
[ -z "$cmd" ] && exit 0

block() {
  echo "[guard] 已拦截：$1" >&2
  echo "[guard] 此操作需人工审批：按 rules/common/server-approval.md 提供完整命令，由用户选「自己执行/帮我执行」" >&2
  exit 2
}

case "$cmd" in
  *"git push"*"--force"*|*"git push -f"*)            block "破坏性 git：force push" ;;
  *"git reset --hard"*)                              block "破坏性 git：reset --hard" ;;
  *"git branch -D"*)                                 block "破坏性 git：删分支" ;;
  *"docker push"*|*"docker rm"*|*"docker restart"*)  block "部署/容器变更" ;;
  *"scp "*|*"rsync "*)                               block "远程传输（部署类）" ;;
esac

case "$cmd" in
  *ssh*)
    case "$cmd" in
      *" rm "*|*" mv "*|*chmod*|*chown*|*"systemctl restart"*|*"systemctl stop"*|*"systemctl start"*|*"systemctl reload"*|*INSERT*|*UPDATE*|*DELETE*|*ALTER*|*DROP*|*TRUNCATE*|*FLUSH*|*"CONFIG SET"*|*">"*|*vim*)
        block "ssh 写操作（只读命令不拦：cat/tail/grep/SELECT/GET 等直通）" ;;
    esac ;;
esac
exit 0
