"""Cache management commands for dg-trpg admins."""

from __future__ import annotations

import logging

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..core.cache_validator import validate_caches
from ..core.context import get_plain_args
from ..core.errors import format_context_error
from ..core.permissions import require_superuser
from ..core.state import get_state

logger = logging.getLogger("dg_trpg.cache_admin")

# ── /cache (/缓存) ───────────────────────────────────────

cache_cmd = on_command("cache", aliases={"缓存"}, priority=10, block=True)


@cache_cmd.handle()
async def handle_cache(
    matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()
) -> None:
    try:
        require_superuser(event)
    except Exception as e:
        msg = format_context_error(e)
        if msg:
            await matcher.finish(msg)
        raise

    text = get_plain_args(args)
    parts = text.split()
    subcmd = parts[0] if parts else "status"
    sub_args = parts[1] if len(parts) > 1 else ""

    if subcmd == "flush":
        await _flush(matcher, sub_args)
    elif subcmd == "validate":
        await _validate(matcher)
    elif subcmd == "status":
        await _status(matcher)
    else:
        await matcher.finish(
            f"未知子命令: {subcmd}\n"
            "用法:\n"
            "/cache status - 查看缓存状态\n"
            "/cache flush [all|user|region|location|session] - 清除缓存\n"
            "/cache validate - 重新验证缓存"
        )


async def _flush(matcher: Matcher, target: str) -> None:
    state = get_state()
    target = target.lower() if target else "all"

    valid_targets = {"all", "user", "region", "location", "session"}
    if target not in valid_targets:
        await matcher.finish(
            f"未知缓存类型: {target}\n"
            f"可选: {', '.join(sorted(valid_targets))}"
        )

    if target == "all":
        counts = state.clear_all()
        total = sum(counts.values())
        lines = [
            "【缓存已清除】",
            f"用户缓存: {counts['user']} 条",
            f"区域绑定: {counts['region']} 条",
            f"地点绑定: {counts['location']} 条",
            f"场次缓存: {counts['session']} 条",
            f"共清除 {total} 条缓存",
        ]
        logger.warning("Admin flushed all caches: %s", counts)
        await matcher.finish("\n".join(lines))
    elif target == "user":
        count = state.clear_all_users()
        logger.warning("Admin flushed user cache: %d entries", count)
        await matcher.finish(f"用户缓存已清除 ({count} 条)")
    elif target == "region":
        count = state.clear_all_regions()
        logger.warning("Admin flushed region cache: %d entries", count)
        await matcher.finish(f"区域绑定已清除 ({count} 条)")
    elif target == "location":
        count = state.clear_all_locations()
        logger.warning("Admin flushed location cache: %d entries", count)
        await matcher.finish(f"地点绑定已清除 ({count} 条)")
    elif target == "session":
        count = state.clear_all_sessions()
        logger.warning("Admin flushed session cache: %d entries", count)
        await matcher.finish(f"场次缓存已清除 ({count} 条)")


async def _validate(matcher: Matcher) -> None:
    await matcher.send("正在验证缓存...")
    await validate_caches()
    await matcher.finish("缓存验证完成，请查看日志了解详细结果。")


async def _status(matcher: Matcher) -> None:
    state = get_state()
    users = state.get_all_users()
    regions = state.get_all_regions()
    locations = state.get_all_locations()
    sessions = state.get_all_sessions()

    lines = [
        "【缓存状态】",
        f"用户缓存: {len(users)} 条",
        f"区域绑定: {len(regions)} 条",
        f"地点绑定: {len(locations)} 条",
        f"场次缓存: {len(sessions)} 条",
    ]
    await matcher.finish("\n".join(lines))
