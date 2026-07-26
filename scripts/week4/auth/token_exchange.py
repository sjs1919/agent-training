"""
Token Exchange 鉴权模块 — 用户身份透传 + 工具级权限

基于 RFC 8693 Token Exchange 模式：
  用户 Token → STS（Security Token Service）→ 受限权限 Token → Agent 调用

洋葱型防御模型：
  网关层（JWT 验证）→ 运行时层（RBAC 权限校验）→ 工具层（二次验证）

角色权限矩阵：
  - admin: 所有操作
  - scheduler: 订单查询 + 资源查询 + 排产建议
  - reviewer: 客户查询 + 订单审核
  - operator: 订单查询 + 设备查询（只读）
  - viewer: 仅订单基本信息
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Literal

RoleType = Literal["admin", "scheduler", "reviewer", "operator", "viewer"]

ROLE_PERMISSIONS: dict[RoleType, list[str]] = {
    "admin":     ["*"],
    "scheduler": ["query_orders", "get_order_detail", "get_production_status",
                  "query_inventory", "query_machine_load", "query_customer"],
    "reviewer":  ["get_order_detail", "get_production_status", "query_customer"],
    "operator":  ["query_orders", "query_machine_load", "query_inventory"],
    "viewer":    ["query_orders"],
}


@dataclass
class Token:
    """JWT Token 的简化表示。"""
    subject: str                # 用户/Agent 身份
    role: RoleType              # 角色
    permissions: list[str]      # 允许调用的工具列表
    source: str                 # 来源："user" | "token_exchange"
    parent_trace: str = ""      # 上游 Trace ID
    issued_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    token_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def is_expired(self) -> bool:
        return self.expires_at > 0 and time.time() > self.expires_at

    def can_access(self, tool_name: str) -> bool:
        if self.is_expired():
            return False
        if "*" in self.permissions:
            return True
        return tool_name in self.permissions


class STS:
    """Security Token Service — Token 签发与交换。"""

    def __init__(self):
        self._issued_tokens: dict[str, Token] = {}

    def issue_user_token(self, user_id: str, role: RoleType, ttl: int = 3600) -> str:
        token = Token(
            subject=user_id, role=role,
            permissions=ROLE_PERMISSIONS.get(role, []),
            source="user", expires_at=time.time() + ttl,
        )
        self._issued_tokens[token.token_id] = token
        return token.token_id

    def exchange(self, parent_token_id: str, requested_role: RoleType,
                 target_trace: str = "") -> tuple[str | None, str]:
        """Token Exchange：父 Token → 受限子 Token。"""
        parent = self._issued_tokens.get(parent_token_id)
        if not parent:
            return None, "父 Token 不存在"
        if parent.is_expired():
            return None, "父 Token 已过期"

        # 权限收缩检查：子 Token 权限不能超过父 Token
        child_perms = ROLE_PERMISSIONS.get(requested_role, [])
        if "*" not in parent.permissions:
            for p in child_perms:
                if p not in parent.permissions:
                    return None, f"权限不足：子角色需要 {p}，父角色没有"

        child = Token(
            subject=f"{parent.subject}:{requested_role}",
            role=requested_role,
            permissions=child_perms,
            source="token_exchange",
            parent_trace=parent.parent_trace or parent.token_id,
            expires_at=time.time() + 300,  # 子 Token 短时效，5 分钟
        )
        self._issued_tokens[child.token_id] = child
        return child.token_id, "ok"

    def validate(self, token_id: str, required_tool: str) -> tuple[bool, str]:
        """验证 Token 是否有权调用指定工具。"""
        token = self._issued_tokens.get(token_id)
        if not token:
            return False, "Token 无效"
        if token.is_expired():
            return False, "Token 已过期"
        if token.can_access(required_tool):
            return True, "ok"
        return False, f"权限不足：需要 {required_tool}，角色 {token.role} 无此权限"

    def revoke(self, token_id: str) -> None:
        """吊销 Token（紧急响应用）。"""
        if token_id in self._issued_tokens:
            del self._issued_tokens[token_id]
            print(f"[鉴权] Token {token_id[:8]}... 已吊销")

    def revoke_all(self) -> None:
        """一键吊销所有 Token（Agent Universal Logout）。"""
        count = len(self._issued_tokens)
        self._issued_tokens.clear()
        print(f"[鉴权] 已吊销 {count} 个 Token（通用注销）")