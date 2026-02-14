from __future__ import annotations

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..core.api_client import get_client
from ..core.context import (
    get_dg_user_id,
    get_game_id,
    get_mentioned_qq_uid,
    get_plain_args,
    get_session_id,
    resolve_player_target,
)
from ..core.errors import DgCoreError, format_api_error, format_context_error
from ..core.formatters import format_comm_list, format_engine_result

# ── /com ───────────────────────────────────────────────────

com_cmd = on_command("com", priority=10, block=True)

_SUBCMDS = {"list", "accept", "reject", "cancel"}


@com_cmd.handle()
async def handle_com(
    matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()
) -> None:
    text = get_plain_args(args)
    parts = text.split(maxsplit=1)
    first = parts[0] if parts else ""
    sub_args = parts[1] if len(parts) > 1 else ""

    try:
        if first in _SUBCMDS:
            handlers = {
                "list": _list,
                "accept": _accept,
                "reject": _reject,
                "cancel": _cancel,
            }
            await handlers[first](matcher, event, args, sub_args)
        elif first or get_mentioned_qq_uid(args):
            await _initiate(matcher, event, args, text)
        else:
            await matcher.finish(
                "用法:\n"
                "/com <@对方|QQ号|角色名> - 发起通信请求\n"
                "/com list - 查看通信请求\n"
                "/com accept <@玩家|QQ号|角色名|通信ID> [能力] - 接受通信\n"
                "/com reject <@玩家|QQ号|角色名|通信ID> - 拒绝通信\n"
                "/com cancel <@玩家|QQ号|角色名|通信ID> - 取消通信"
            )
    except DgCoreError as e:
        await matcher.finish(format_api_error(e))
    except Exception as e:
        msg = format_context_error(e)
        if msg:
            await matcher.finish(msg)
        raise


async def _initiate(
    matcher: Matcher,
    event: GroupMessageEvent,
    args: Message,
    text: str,
) -> None:
    game_id = get_game_id()
    user_id = await get_dg_user_id(event)

    target_user_id = await resolve_player_target(args, text)
    if not target_user_id:
        await matcher.finish("用法: /com <@对方|QQ号|角色名>")

    try:
        session_id = get_session_id(event)
    except Exception:
        session_id = None

    client = get_client()
    data = await client.submit_event(
        game_id,
        session_id,
        user_id,
        {"event_type": "comm_request", "target_patient_id": target_user_id},
    )
    await matcher.finish(format_engine_result(data))


async def _list(
    matcher: Matcher,
    event: GroupMessageEvent,
    args: Message,
    sub_args: str,
) -> None:
    game_id = get_game_id()
    user_id = await get_dg_user_id(event)

    client = get_client()
    data = await client.list_pending_comms(game_id, user_id)
    await matcher.finish(format_comm_list(data))


async def _accept(
    matcher: Matcher,
    event: GroupMessageEvent,
    args: Message,
    sub_args: str,
) -> None:
    game_id = get_game_id()
    user_id = await get_dg_user_id(event)

    parts = sub_args.split()

    request_id = ""
    ability_id: str | None = None

    resolved = await resolve_player_target(args, parts[0] if parts else "")
    if resolved:
        request_id = resolved
    elif parts:
        request_id = parts[0]

    if len(parts) > 1:
        ability_id = parts[1]

    if not request_id:
        await matcher.finish("用法: /com accept <@玩家|QQ号|角色名|通信ID> [打印能力名称]")

    try:
        session_id = get_session_id(event)
    except Exception:
        session_id = None

    payload: dict = {
        "event_type": "comm_accept",
        "request_id": request_id,
    }
    if ability_id:
        payload["ability_id"] = ability_id

    client = get_client()
    data = await client.submit_event(game_id, session_id, user_id, payload)
    await matcher.finish(format_engine_result(data))


async def _reject(
    matcher: Matcher,
    event: GroupMessageEvent,
    args: Message,
    sub_args: str,
) -> None:
    game_id = get_game_id()
    user_id = await get_dg_user_id(event)

    request_id = await resolve_player_target(args, sub_args) or ""

    if not request_id:
        await matcher.finish("用法: /com reject <@玩家|QQ号|角色名|通信ID>")

    try:
        session_id = get_session_id(event)
    except Exception:
        session_id = None

    client = get_client()
    data = await client.submit_event(
        game_id,
        session_id,
        user_id,
        {"event_type": "comm_reject", "request_id": request_id},
    )
    await matcher.finish(format_engine_result(data))


async def _cancel(
    matcher: Matcher,
    event: GroupMessageEvent,
    args: Message,
    sub_args: str,
) -> None:
    game_id = get_game_id()
    user_id = await get_dg_user_id(event)

    request_id = await resolve_player_target(args, sub_args) or ""

    if not request_id:
        await matcher.finish("用法: /com cancel <@玩家|QQ号|角色名|通信ID>")

    try:
        session_id = get_session_id(event)
    except Exception:
        session_id = None

    client = get_client()
    data = await client.submit_event(
        game_id,
        session_id,
        user_id,
        {"event_type": "comm_cancel", "request_id": request_id},
    )
    await matcher.finish(format_engine_result(data))
