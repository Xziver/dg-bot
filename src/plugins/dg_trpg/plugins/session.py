from __future__ import annotations

from nonebot import logger, on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..core.api_client import get_client
from ..core.context import (
    get_dg_user_id,
    get_game_id,
    get_group_id,
    get_location_id,
    get_plain_args,
    get_session_id,
    handle_stale_cache_404,
    resolve_player_target,
)
from ..core.errors import DgCoreError, NoActiveSession, format_api_error, format_context_error
from ..core.formatters import format_engine_result, format_session_info
from ..core.permissions import require_group_admin_or_superuser
from ..core.state import get_state

# ── /session ───────────────────────────────────────────────

session_cmd = on_command("session", priority=10, block=True)


@session_cmd.handle()
async def handle_session(
    matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()
) -> None:
    text = get_plain_args(args)
    parts = text.split(maxsplit=1)
    subcmd = parts[0] if parts else "info"
    sub_args = parts[1] if len(parts) > 1 else ""

    try:
        handlers = {
            "start": _start,
            "end": _end,
            "pause": _pause,
            "resume": _resume,
            "info": _info,
            "add": _add,
            "remove": _remove,
        }
        handler = handlers.get(subcmd)
        if handler:
            await handler(matcher, event, args, sub_args)
        else:
            await matcher.finish(
                f"未知子命令: {subcmd}\n"
                "用法: /session [start|end|pause|resume|info|add|remove]"
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


async def _start(
    matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str
) -> None:
    require_group_admin_or_superuser(event)
    game_id = get_game_id()
    user_id = await get_dg_user_id(event)
    group_id = get_group_id(event)

    # Check if this group already has an active session
    state = get_state()
    existing_session_id = state.get_session(group_id)
    if existing_session_id:
        # Verify the cached session is still active on the backend
        client = get_client()
        try:
            info = await client.get_session_info(existing_session_id)
            status = info.get("status", info.get("data", {}).get("status", ""))
            if status in ("active", "paused"):
                await matcher.finish(
                    f"本群已有进行中的场次 (ID: {existing_session_id})。\n"
                    "请先使用 /session end 结束当前场次，再开始新场次。"
                )
        except DgCoreError as e:
            if e.status_code == 404:
                # Cached session no longer exists on backend, clear stale cache
                state.clear_session(group_id)
                logger.warning("Stale session cleared during start: group={}", group_id)
            else:
                raise

    # Get bound location for this group
    try:
        location_id = get_location_id(event)
    except Exception:
        location_id = None

    payload: dict = {"event_type": "session_start"}
    if location_id:
        payload["location_id"] = location_id

    # Also try to include region_id
    region = state.get_region(group_id)
    if region:
        payload["region_id"] = region["region_id"]

    client = get_client()
    data = await client.submit_event(game_id, None, user_id, payload)

    # Cache session ID
    session_id = data.get("data", {}).get("session_id", data.get("session_id", ""))
    if session_id:
        state.set_session(group_id, session_id)
        logger.info("Session started: group={}, session_id={}", group_id, session_id)

    if data.get("success"):
        msg = "场次已开始！"
        if session_id:
            msg += f"\nSession ID: {session_id}"
        await matcher.finish(msg)
    else:
        await matcher.finish(format_engine_result(data))


async def _end(
    matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str
) -> None:
    require_group_admin_or_superuser(event)
    game_id = get_game_id()
    session_id = get_session_id(event)
    user_id = await get_dg_user_id(event)
    group_id = get_group_id(event)

    client = get_client()
    data = await client.submit_event(
        game_id, session_id, user_id, {"event_type": "session_end"}
    )

    # Clear session cache
    get_state().clear_session(group_id)
    logger.info("Session ended: group={}", group_id)

    if data.get("success"):
        await matcher.finish("场次已结束。")
    else:
        await matcher.finish(format_engine_result(data))


async def _pause(
    matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str
) -> None:
    require_group_admin_or_superuser(event)
    session_id = get_session_id(event)
    user_id = await get_dg_user_id(event)

    client = get_client()
    await client.pause_session(session_id, user_id=user_id)
    logger.info("Session paused: session_id={}", session_id)
    await matcher.finish("场次已暂停。")


async def _resume(
    matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str
) -> None:
    require_group_admin_or_superuser(event)
    session_id = get_session_id(event)
    user_id = await get_dg_user_id(event)

    client = get_client()
    await client.resume_session(session_id, user_id=user_id)
    logger.info("Session resumed: session_id={}", session_id)
    await matcher.finish("场次已恢复。")


async def _info(
    matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str
) -> None:
    group_id = get_group_id(event)
    state = get_state()
    session_id = state.get_session(group_id)

    if not session_id:
        location = state.get_location(group_id)
        if location:
            loc_name = location.get("location_name", "未知")
            await matcher.finish(
                f"当前地点是{loc_name}，但没有任何活动的Session。\n"
                "DM可以使用 /session start 创建一个新的Session！"
            )
        else:
            await matcher.finish(
                "当前没有活动的Session，且本群未绑定地点。\n"
                "DM请先使用 /location bind <地点名称> 绑定地点。"
            )

    client = get_client()
    try:
        data = await client.get_session_info(session_id)
        await matcher.finish(format_session_info(data))
    except DgCoreError as e:
        if e.status_code == 404:
            state.clear_session(group_id)
            logger.warning("Stale session cleared during info: group={}", group_id)
            await matcher.finish("缓存的场次已失效，已清除。请DM使用 /session start 创建新场次。")
        raise


async def _add(
    matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str
) -> None:
    require_group_admin_or_superuser(event)
    game_id = get_game_id()
    session_id = get_session_id(event)
    user_id = await get_dg_user_id(event)

    target_user_id = await resolve_player_target(args, sub_args)
    if not target_user_id:
        await matcher.finish("用法: /session add <@玩家|QQ号|角色名>")
        return

    # Resolve target's active patient_id (v2 API requires patient_id, not user_id)
    client = get_client()
    char_data = await client.get_active_character(game_id, target_user_id)
    patient = char_data.get("patient") or char_data.get("active_patient") or {}
    patient_id = patient.get("patient_id", patient.get("id", ""))
    if not patient_id:
        await matcher.finish("目标玩家没有活跃的患者角色，无法加入场次。")
        return

    await client.add_session_player(session_id, patient_id, user_id=user_id)
    await matcher.finish("玩家已添加到当前场次。")


async def _remove(
    matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str
) -> None:
    require_group_admin_or_superuser(event)
    game_id = get_game_id()
    session_id = get_session_id(event)
    user_id = await get_dg_user_id(event)

    target_user_id = await resolve_player_target(args, sub_args)
    if not target_user_id:
        await matcher.finish("用法: /session remove <@玩家|QQ号|角色名>")
        return

    # Resolve target's active patient_id (v2 API requires patient_id in path)
    client = get_client()
    char_data = await client.get_active_character(game_id, target_user_id)
    patient = char_data.get("patient") or char_data.get("active_patient") or {}
    patient_id = patient.get("patient_id", patient.get("id", ""))
    if not patient_id:
        await matcher.finish("目标玩家没有活跃的患者角色。")
        return

    await client.remove_session_player(session_id, patient_id, user_id=user_id)
    await matcher.finish("玩家已从当前场次移除。")
