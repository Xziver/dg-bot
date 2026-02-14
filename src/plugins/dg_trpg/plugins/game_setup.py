from __future__ import annotations

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..core.api_client import get_client
from ..core.context import (
    get_dg_user_id,
    get_game_id,
    get_plain_args,
    get_mentioned_qq_uid,
    resolve_player_target,
)
from ..core.errors import DgCoreError, format_api_error, format_context_error

# ── /game ─────────────────────────────────────────────────

game_cmd = on_command("game", priority=10, block=True)


@game_cmd.handle()
async def handle_game(
    matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()
) -> None:
    text = get_plain_args(args)
    parts = text.split(maxsplit=1)
    subcmd = parts[0] if parts else "info"
    sub_args = parts[1] if len(parts) > 1 else ""

    try:
        handlers = {
            "join": _join,
            "info": _info,
            "add": _add,
            "role": _role,
        }
        handler = handlers.get(subcmd)
        if handler:
            await handler(matcher, event, args, sub_args)
        else:
            await matcher.finish(
                f"未知子命令: {subcmd}\n"
                "用法: /game [join|info|add|role]"
            )
    except DgCoreError as e:
        await matcher.finish(format_api_error(e))
    except Exception as e:
        msg = format_context_error(e)
        if msg:
            await matcher.finish(msg)
        raise


async def _join(
    matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str
) -> None:
    """Player joins the global game as PL."""
    game_id = get_game_id()
    user_id = await get_dg_user_id(event)

    role = sub_args.strip().upper() if sub_args.strip() else "PL"
    if role not in ("PL", "DM"):
        await matcher.finish("角色必须是 PL 或 DM。")

    client = get_client()
    try:
        await client.add_game_player(game_id, user_id, role=role)
    except DgCoreError as e:
        if e.status_code in (400, 409) and "UNIQUE" in e.detail:
            await matcher.finish(
                "你已经加入了该游戏。\n"
                "如需切换身份，请使用 /game role <PL|DM>"
            )
        raise
    role_label = "玩家(PL)" if role == "PL" else "主持人(DM)"
    await matcher.finish(f"加入游戏成功！身份: {role_label}")


async def _role(
    matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str
) -> None:
    """Switch player role between PL and DM."""
    role = sub_args.strip().upper()
    if role not in ("PL", "DM"):
        await matcher.finish("用法: /game role <PL|DM>")

    game_id = get_game_id()
    user_id = await get_dg_user_id(event)

    client = get_client()
    await client.update_game_player_role(game_id, user_id, role)
    role_label = "玩家(PL)" if role == "PL" else "主持人(DM)"
    await matcher.finish(f"身份切换成功！当前身份: {role_label}")


async def _info(
    matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str
) -> None:
    """View game info."""
    game_id = get_game_id()
    client = get_client()
    data = await client.get_game_info(game_id)

    name = data.get("name", "未知")
    status = data.get("status", "未知")
    players = data.get("players", [])

    lines = ["【游戏信息】"]
    lines.append(f"名称: {name}")
    lines.append(f"状态: {status}")
    lines.append(f"Game ID: {game_id}")

    if players:
        player_strs = []
        for p in players:
            uname = p.get("username", p.get("name", "?"))
            role = p.get("role", "?")
            player_strs.append(f"{uname}({role})")
        lines.append(f"玩家: {', '.join(player_strs)}")
    else:
        lines.append("玩家: 无")

    await matcher.finish("\n".join(lines))


async def _add(
    matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str
) -> None:
    """DM adds a player to the game."""
    mentioned = get_mentioned_qq_uid(args)
    parts = sub_args.split()

    # Separate player reference from role token
    role = "PL"
    player_ref = ""
    if mentioned:
        # @mention: player from mention, role from plain text
        player_ref = ""  # resolve_player_target will use @mention
        for token in parts:
            if token.upper() in ("PL", "DM"):
                role = token.upper()
    else:
        for token in parts:
            if token.upper() in ("PL", "DM"):
                role = token.upper()
            elif not player_ref:
                player_ref = token

    target_user_id = await resolve_player_target(args, player_ref)
    if not target_user_id:
        await matcher.finish("用法: /game add <@玩家|QQ号|角色名> [PL|DM]")

    game_id = get_game_id()
    user_id = await get_dg_user_id(event)

    client = get_client()
    try:
        await client.add_game_player(game_id, target_user_id, role=role)
    except DgCoreError as e:
        if e.status_code in (400, 409) and "UNIQUE" in e.detail:
            await matcher.finish("该玩家已在游戏中。")
        raise
    role_label = "玩家(PL)" if role == "PL" else "主持人(DM)"
    await matcher.finish(f"已将玩家添加到游戏，身份: {role_label}")
