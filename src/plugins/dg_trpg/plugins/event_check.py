from __future__ import annotations

from typing import Any

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..core.api_client import get_client
from ..core.context import get_dg_user_id, get_game_id, get_group_id, get_plain_args, get_session_id
from ..core.errors import DgCoreError, format_api_error, format_context_error
from ..core.formatters import format_engine_result, format_event_check, format_event_list
from ..core.state import get_state

# ── /event ─────────────────────────────────────────────────

event_cmd = on_command("event", priority=10, block=True)


@event_cmd.handle()
async def handle_event(
    matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()
) -> None:
    text = get_plain_args(args)
    parts = text.split(maxsplit=1)
    subcmd = parts[0] if parts else "list"
    sub_args = parts[1] if len(parts) > 1 else ""

    try:
        handlers = {
            "set": _set,
            "check": _check,
            "list": _list,
            "delete": _delete,
        }
        handler = handlers.get(subcmd)
        if handler:
            await handler(matcher, event, sub_args)
        else:
            await matcher.finish(
                f"未知子命令: {subcmd}\n"
                "用法: /event [set|check|list|delete]"
            )
    except DgCoreError as e:
        await matcher.finish(format_api_error(e))
    except Exception as e:
        msg = format_context_error(e)
        if msg:
            await matcher.finish(msg)
        raise


async def _set(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    parts = sub_args.split()
    if len(parts) < 2:
        await matcher.finish(
            "用法: /event set <事件名称> <骰子表达式> [限定颜色]\n"
            "例: /event set 潜行 2d6+2 c"
        )

    name = parts[0]
    expression = parts[1]
    color: str | None = parts[2].upper() if len(parts) > 2 else None

    game_id = get_game_id()
    session_id = get_session_id(event)
    user_id = await get_dg_user_id(event)

    client = get_client()
    await client.define_event(
        session_id, game_id, name, expression,
        color_restriction=color, user_id=user_id,
    )

    color_text = f" [限定: {color}]" if color else ""
    await matcher.finish(f"事件设定成功！{name}: {expression}{color_text}")


async def _check(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    parts = sub_args.split()
    if not parts:
        await matcher.finish(
            "用法: /event check <事件名称> [骰子颜色]\n"
            "例: /event check 潜行 c"
        )

    event_name = parts[0]
    color: str | None = parts[1].upper() if len(parts) > 1 else None

    game_id = get_game_id()
    session_id = get_session_id(event)
    user_id = await get_dg_user_id(event)

    payload: dict = {
        "event_type": "event_check",
        "event_name": event_name,
    }
    if color:
        payload["color"] = color

    client = get_client()
    data = await client.submit_event(game_id, session_id, user_id, payload)

    # Cache event_name for subsequent /re and /hre commands
    if data.get("success"):
        group_id = get_group_id(event)
        get_state().set_last_event_check(group_id, user_id, event_name)

    # Format specifically for event check results
    if data.get("success") and data.get("data"):
        check_data = data["data"]
        check_data.setdefault("event_name", event_name)
        await matcher.finish(format_event_check(check_data))
    else:
        await matcher.finish(format_engine_result(data))


async def _list(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    session_id = get_session_id(event)

    client = get_client()
    data = await client.list_events(session_id)
    await matcher.finish(format_event_list(data))


async def _delete(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    if not sub_args:
        await matcher.finish("用法: /event delete <事件名称>")

    event_name = sub_args.strip()
    game_id = get_game_id()
    session_id = get_session_id(event)
    user_id = await get_dg_user_id(event)

    # Find event ID by name
    client = get_client()
    events = await client.list_events(session_id)
    event_id = None
    for ev in events:
        if ev.get("name") == event_name or ev.get("id") == event_name:
            event_id = ev.get("id")
            break

    if not event_id:
        await matcher.finish(f"未找到名为 '{event_name}' 的事件。")

    await client.delete_event(session_id, event_id, game_id=game_id, user_id=user_id)
    await matcher.finish(f"事件 '{event_name}' 已删除。")


# ── Helper: resolve ability name → ability_id ────────────

async def _resolve_ability_id(
    client: Any, game_id: str, user_id: str, ability_name: str
) -> str:
    """Resolve an ability name to its UUID by looking up the player's ghost abilities."""
    char_data = await client.get_active_character(game_id, user_id)
    ghost = char_data.get("ghost") or char_data.get("active_ghost") or {}
    ghost_id = ghost.get("ghost_id", ghost.get("id", ""))
    if not ghost_id:
        raise DgCoreError(0, "当前没有活跃的幽灵角色。")

    abilities = await client.get_abilities(ghost_id, game_id=game_id)
    for a in abilities:
        if a.get("name") == ability_name or a.get("id") == ability_name:
            return a.get("id", ability_name)
    # Fallback: pass the name as-is and let the backend handle the error
    return ability_name


# ── /re (同色重投) ─────────────────────────────────────────

re_cmd = on_command("re", priority=10, block=True)


@re_cmd.handle()
async def handle_re(
    matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()
) -> None:
    text = get_plain_args(args)
    if not text:
        await matcher.finish("用法: /re <同色打印能力名称>\n例: /re 火球术")

    ability_name = text.strip()

    try:
        game_id = get_game_id()
        session_id = get_session_id(event)
        user_id = await get_dg_user_id(event)
        group_id = get_group_id(event)

        # Retrieve cached event_name from last /event check
        event_name = get_state().get_last_event_check(group_id, user_id)
        if not event_name:
            await matcher.finish("你还没有进行过检定，请先使用 /event check 进行检定。")

        # Resolve ability name → ability_id
        client = get_client()
        ability_id = await _resolve_ability_id(client, game_id, user_id, ability_name)

        data = await client.submit_event(
            game_id,
            session_id,
            user_id,
            {"event_type": "reroll", "event_name": event_name, "ability_id": ability_id},
        )

        if data.get("success") and data.get("data"):
            check_data = data["data"]
            await matcher.finish(format_event_check(check_data))
        else:
            await matcher.finish(format_engine_result(data))
    except DgCoreError as e:
        await matcher.finish(format_api_error(e))
    except Exception as e:
        msg = format_context_error(e)
        if msg:
            await matcher.finish(msg)
        raise


# ── /hre (异色重投) ────────────────────────────────────────

hre_cmd = on_command("hre", priority=10, block=True)


@hre_cmd.handle()
async def handle_hre(
    matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()
) -> None:
    text = get_plain_args(args)
    if not text:
        await matcher.finish("用法: /hre <任意打印能力名称>\n消耗1MP进行异色重投。\n例: /hre 强壮")

    ability_name = text.strip()

    try:
        game_id = get_game_id()
        session_id = get_session_id(event)
        user_id = await get_dg_user_id(event)
        group_id = get_group_id(event)

        # Retrieve cached event_name from last /event check
        event_name = get_state().get_last_event_check(group_id, user_id)
        if not event_name:
            await matcher.finish("你还没有进行过检定，请先使用 /event check 进行检定。")

        # Resolve ability name → ability_id
        client = get_client()
        ability_id = await _resolve_ability_id(client, game_id, user_id, ability_name)

        data = await client.submit_event(
            game_id,
            session_id,
            user_id,
            {"event_type": "hard_reroll", "event_name": event_name, "ability_id": ability_id},
        )

        if data.get("success") and data.get("data"):
            check_data = data["data"]
            await matcher.finish(format_event_check(check_data))
        else:
            await matcher.finish(format_engine_result(data))
    except DgCoreError as e:
        await matcher.finish(format_api_error(e))
    except Exception as e:
        msg = format_context_error(e)
        if msg:
            await matcher.finish(msg)
        raise
