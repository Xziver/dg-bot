from __future__ import annotations

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..core.api_client import get_client
from ..core.context import (
    extract_target_from_args,
    get_dg_user_id,
    get_game_id,
    get_plain_args,
    resolve_player_target,
)
from ..core.errors import DgCoreError, format_api_error, format_context_error
from ..core.formatters import format_buff_list, format_engine_result

# ── /buff ──────────────────────────────────────────────────

buff_cmd = on_command("buff", priority=10, block=True)


@buff_cmd.handle()
async def handle_buff(
    matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()
) -> None:
    text = get_plain_args(args)
    parts = text.split(maxsplit=1)
    subcmd = parts[0] if parts else "show"
    sub_args = parts[1] if len(parts) > 1 else ""

    try:
        handlers = {
            "add": _add,
            "show": _show,
            "remove": _remove,
        }
        handler = handlers.get(subcmd)
        if handler:
            await handler(matcher, event, args, sub_args)
        else:
            await matcher.finish(
                f"未知子命令: {subcmd}\n用法: /buff [add|show|remove]"
            )
    except DgCoreError as e:
        await matcher.finish(format_api_error(e))
    except Exception as e:
        msg = format_context_error(e)
        if msg:
            await matcher.finish(msg)
        raise


async def _add(matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str) -> None:
    target_user_id, remaining = await extract_target_from_args(args, sub_args)

    parts = remaining.split()
    if len(parts) < 2:
        await matcher.finish(
            "用法: /buff add [@目标] <名称> <表达式> [持续回合数]\n"
            "例: /buff add 强壮 1d6+3 3\n"
            "例: /buff add @玩家 强壮 1d6+3 3"
        )

    name = parts[0]
    expression = parts[1]
    rounds = 1
    if len(parts) > 2:
        try:
            rounds = int(parts[2])
        except ValueError:
            pass

    game_id = get_game_id()
    sender_user_id = await get_dg_user_id(event)
    char_owner = target_user_id or sender_user_id

    client = get_client()
    char_data = await client.get_active_character(game_id, char_owner)
    ghost = char_data.get("ghost") or char_data.get("active_ghost") or {}
    ghost_id = ghost.get("ghost_id", ghost.get("id", ""))
    if not ghost_id:
        if target_user_id:
            await matcher.finish("目标玩家当前没有活跃的幽灵角色。")
        else:
            await matcher.finish("当前没有活跃的幽灵角色。")

    data = await client.add_buff(
        game_id, ghost_id, name, expression,
        rounds=rounds, user_id=sender_user_id,
    )

    if not data.get("success", True):
        await matcher.finish(format_engine_result(data))

    rounds_text = "永久" if rounds == -1 else f"{rounds}轮"
    target_label = f" → {ghost.get('name', '目标')}" if target_user_id else ""
    await matcher.finish(f"BUFF添加成功！{name} ({expression}) [{rounds_text}]{target_label}")


async def _show(matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str) -> None:
    game_id = get_game_id()
    target = await resolve_player_target(args, sub_args)
    user_id = target if target else await get_dg_user_id(event)

    client = get_client()
    char_data = await client.get_active_character(game_id, user_id)
    ghost = char_data.get("ghost") or char_data.get("active_ghost") or {}
    ghost_id = ghost.get("ghost_id", ghost.get("id", ""))
    if not ghost_id:
        await matcher.finish("当前没有活跃的幽灵角色。")

    data = await client.list_buffs(game_id, ghost_id)
    await matcher.finish(format_buff_list(data))


async def _remove(matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str) -> None:
    target_user_id, remaining = await extract_target_from_args(args, sub_args)

    if not remaining:
        await matcher.finish(
            "用法: /buff remove [@目标] <BUFF名称>\n"
            "例: /buff remove 强壮\n"
            "例: /buff remove @玩家 强壮"
        )

    buff_name = remaining.strip()
    game_id = get_game_id()
    sender_user_id = await get_dg_user_id(event)
    char_owner = target_user_id or sender_user_id

    client = get_client()
    char_data = await client.get_active_character(game_id, char_owner)
    ghost = char_data.get("ghost") or char_data.get("active_ghost") or {}
    ghost_id = ghost.get("ghost_id", ghost.get("id", ""))
    if not ghost_id:
        if target_user_id:
            await matcher.finish("目标玩家当前没有活跃的幽灵角色。")
        else:
            await matcher.finish("当前没有活跃的幽灵角色。")

    buffs = await client.list_buffs(game_id, ghost_id)
    buff_id = None
    for b in buffs:
        if b.get("name") == buff_name or b.get("id") == buff_name:
            buff_id = b.get("id")
            break

    if not buff_id:
        await matcher.finish(f"未找到名为 '{buff_name}' 的BUFF。")

    data = await client.remove_buff(game_id, buff_id, user_id=sender_user_id)

    if not data.get("success", True):
        await matcher.finish(format_engine_result(data))

    target_label = f" ({ghost.get('name', '目标')})" if target_user_id else ""
    await matcher.finish(f"BUFF '{buff_name}' 已移除。{target_label}")
