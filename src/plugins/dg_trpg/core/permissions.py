from __future__ import annotations

from nonebot.adapters.onebot.v11 import GroupMessageEvent

from .errors import InsufficientPermission


def is_superuser(event: GroupMessageEvent) -> bool:
    """Check if the message sender is a bot superuser."""
    from nonebot import get_driver

    superusers = get_driver().config.superusers
    return str(event.user_id) in superusers


def is_group_admin(event: GroupMessageEvent) -> bool:
    """Check if the message sender is a group admin or owner."""
    return event.sender.role in ("admin", "owner")


def require_superuser(event: GroupMessageEvent) -> None:
    if not is_superuser(event):
        raise InsufficientPermission("仅超级管理员可执行此操作")


def require_group_admin_or_superuser(event: GroupMessageEvent) -> None:
    if not is_group_admin(event) and not is_superuser(event):
        raise InsufficientPermission("仅群管理员或超级管理员可执行此操作")
