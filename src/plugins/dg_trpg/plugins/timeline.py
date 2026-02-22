from __future__ import annotations

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..core.api_client import get_client
from ..core.context import get_game_id, get_group_id, get_plain_args, get_session_id, handle_stale_cache_404
from ..core.errors import DgCoreError, format_api_error, format_context_error
from ..core.formatters import format_timeline
from ..core.state import get_state

# ── /timeline ──────────────────────────────────────────────

timeline_cmd = on_command("timeline", priority=10, block=True)


@timeline_cmd.handle()
async def handle_timeline(
    matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()
) -> None:
    text = get_plain_args(args)
    parts = text.split(maxsplit=1)
    subcmd = parts[0] if parts else "info"
    sub_args = parts[1] if len(parts) > 1 else ""

    try:
        handlers = {
            "info": _info,
            "export": _export,
            "game": _game,
            "restore": _restore,
        }
        handler = handlers.get(subcmd)
        if handler:
            await handler(matcher, event, sub_args)
        else:
            # Maybe the first arg is a count number
            try:
                count = int(subcmd)
                await _info(matcher, event, subcmd)
            except ValueError:
                await matcher.finish(
                    f"未知子命令: {subcmd}\n"
                    "用法: /timeline [info|export|game|restore]"
                )
    except DgCoreError as e:
        if e.status_code == 404:
            handle_stale_cache_404(e, get_group_id(event), used_session=True)
        await matcher.finish(format_api_error(e))
    except Exception as e:
        msg = format_context_error(e)
        if msg:
            await matcher.finish(msg)
        raise


async def _info(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    session_id = get_session_id(event)

    count: int | None = None
    if sub_args.strip():
        try:
            count = int(sub_args.strip())
        except ValueError:
            pass

    client = get_client()
    data = await client.get_session_timeline(session_id, limit=count)
    await matcher.finish(format_timeline(data))


async def _export(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    session_id = get_session_id(event)

    client = get_client()
    data = await client.get_session_timeline(session_id)

    if not data:
        await matcher.finish("暂无时间线记录可导出。")

    # Format as exportable text
    lines = ["=== 时间线导出 ==="]
    for entry in data:
        ts = entry.get("timestamp", "")
        event_type = entry.get("event_type", "?")
        entry_data = entry.get("data") or {}
        summary = entry_data.get("summary", entry_data.get("description", ""))
        detail = f": {summary}" if summary else ""
        lines.append(f"[{ts}] {event_type}{detail}")
    lines.append("=== 导出结束 ===")

    await matcher.finish("\n".join(lines))


async def _game(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    game_id = get_game_id()

    count: int | None = None
    if sub_args.strip():
        try:
            count = int(sub_args.strip())
        except ValueError:
            pass

    client = get_client()
    data = await client.get_game_timeline(game_id, limit=count)
    await matcher.finish(format_timeline(data))


async def _restore(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    await matcher.finish(
        "功能暂未完全实现：时间线恢复需要上传聊天记录文件。\n"
        "请联系管理员通过后台API进行数据恢复。"
    )
