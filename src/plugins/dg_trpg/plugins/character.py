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
    resolve_patient_id,
    resolve_player_target,
)
from ..core.errors import DgCoreError, format_api_error, format_context_error
from ..core.formatters import format_abilities, format_character, format_character_list

# ── /character ─────────────────────────────────────────────

character_cmd = on_command("character", priority=10, block=True)


@character_cmd.handle()
async def handle_character(
    matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()
) -> None:
    text = get_plain_args(args)
    parts = text.split(maxsplit=1)
    subcmd = parts[0] if parts else "show"
    sub_args = parts[1] if len(parts) > 1 else ""

    try:
        handlers = {
            "show": _show,
            "list": _list,
            "switch": _switch,
            "set": _set,
            "delete": _delete,
            "move": _move,
            "create": _create,
        }
        handler = handlers.get(subcmd)
        if handler:
            await handler(matcher, event, args, sub_args)
        else:
            await matcher.finish(
                f"未知子命令: {subcmd}\n"
                "用法: /character [show|list|switch|set|delete|move|create]"
            )
    except DgCoreError as e:
        await matcher.finish(format_api_error(e))
    except Exception as e:
        msg = format_context_error(e)
        if msg:
            await matcher.finish(msg)
        raise


async def _show(
    matcher: Matcher,
    event: GroupMessageEvent,
    args: Message,
    sub_args: str,
) -> None:
    game_id = get_game_id()
    target = await resolve_player_target(args, sub_args)
    user_id = target if target else await get_dg_user_id(event)

    client = get_client()
    data = await client.get_active_character(game_id, user_id)
    await matcher.finish(format_character(data))


async def _list(
    matcher: Matcher,
    event: GroupMessageEvent,
    args: Message,
    sub_args: str,
) -> None:
    game_id = get_game_id()
    target = await resolve_player_target(args, sub_args)
    user_id = target if target else await get_dg_user_id(event)

    client = get_client()
    data = await client.list_characters(game_id, user_id)
    await matcher.finish(format_character_list(data))


async def _switch(
    matcher: Matcher,
    event: GroupMessageEvent,
    args: Message,
    sub_args: str,
) -> None:
    if not sub_args:
        await matcher.finish("用法: /character switch <角色名称|角色ID>")

    game_id = get_game_id()
    user_id = await get_dg_user_id(event)
    target = sub_args.strip()

    patient_id = await resolve_patient_id(game_id, user_id, target)

    client = get_client()
    data = await client.switch_character(game_id, user_id, patient_id)
    name = data.get("name", data.get("patient_name", target))
    await matcher.finish(f"角色切换成功！当前角色: {name}")


async def _set(
    matcher: Matcher,
    event: GroupMessageEvent,
    args: Message,
    sub_args: str,
) -> None:
    target_user_id, remaining = await extract_target_from_args(args, sub_args)

    parts = remaining.split()
    if len(parts) < 2:
        await matcher.finish(
            "用法: /character set [@目标] <属性名称> <新值>\n"
            "例: /character set health 5\n"
            "例: /character set @玩家 health 5"
        )

    attr_name = parts[0]
    value = parts[1]
    try:
        value_parsed: int | str = int(value)
    except ValueError:
        value_parsed = value

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

    data = await client.set_attribute(
        game_id, sender_user_id, ghost_id, attr_name, value_parsed
    )
    target_label = f" ({ghost.get('name', '目标')})" if target_user_id else ""
    await matcher.finish(f"属性修改成功！{attr_name} → {value_parsed}{target_label}")


async def _delete(
    matcher: Matcher,
    event: GroupMessageEvent,
    args: Message,
    sub_args: str,
) -> None:
    target_user_id, remaining = await extract_target_from_args(args, sub_args)

    if not remaining:
        await matcher.finish(
            "用法: /character delete [@目标] <角色名称|角色ID>\n"
            "例: /character delete 林墨\n"
            "例: /character delete @玩家 林墨"
        )

    game_id = get_game_id()
    sender_user_id = await get_dg_user_id(event)
    char_owner = target_user_id or sender_user_id
    target = remaining.strip()

    patient_id = await resolve_patient_id(game_id, char_owner, target)

    client = get_client()
    await client.delete_character(game_id, patient_id, sender_user_id)
    target_label = f" ({char_owner})" if target_user_id else ""
    await matcher.finish(f"角色 {target} 已删除。{target_label}")


async def _move(
    matcher: Matcher,
    event: GroupMessageEvent,
    args: Message,
    sub_args: str,
) -> None:
    if not sub_args:
        await matcher.finish("用法: /character move <地点名称>")

    game_id = get_game_id()
    user_id = await get_dg_user_id(event)
    location_name = sub_args.strip()

    client = get_client()
    from ..core.context import get_session_id

    try:
        session_id = get_session_id(event)
    except Exception:
        session_id = None

    data = await client.submit_event(
        game_id,
        session_id,
        user_id,
        {"event_type": "location_transition", "target_location_name": location_name},
    )

    if data.get("success"):
        await matcher.finish(f"角色已移动到: {location_name}")
    else:
        error = data.get("error", "移动失败")
        await matcher.finish(f"移动失败: {error}")


async def _create(
    matcher: Matcher,
    event: GroupMessageEvent,
    args: Message,
    sub_args: str,
) -> None:
    parts = sub_args.split()
    if not parts:
        await matcher.finish(
            "用法:\n"
            "/character create patient <名称> <颜色> [性别] [年龄] [身份]\n"
            "/character create ghost [HP]"
        )

    char_type = parts[0].lower()
    remaining = parts[1:]

    if char_type == "patient":
        await _create_patient(matcher, event, remaining)
    elif char_type == "ghost":
        await _create_ghost(matcher, event, remaining)
    else:
        await matcher.finish("角色类型必须是 patient 或 ghost。")


async def _create_patient(
    matcher: Matcher, event: GroupMessageEvent, parts: list[str]
) -> None:
    if len(parts) < 2:
        await matcher.finish(
            "用法: /character create patient <名称> <颜色> [性别] [年龄] [身份]"
        )

    name = parts[0]
    color = parts[1].upper()
    gender = parts[2] if len(parts) > 2 else ""
    age: int | None = None
    identity = ""
    if len(parts) > 3:
        try:
            age = int(parts[3])
        except ValueError:
            identity = parts[3]
    if len(parts) > 4:
        identity = parts[4]

    game_id = get_game_id()
    user_id = await get_dg_user_id(event)
    client = get_client()
    data = await client.create_patient(
        game_id, name, color, user_id, gender=gender, age=age, identity=identity
    )
    patient_name = data.get("name", name)
    await matcher.finish(f"患者角色创建成功！名称: {patient_name}")


async def _create_ghost(
    matcher: Matcher, event: GroupMessageEvent, parts: list[str]
) -> None:
    hp: int | None = None
    if parts:
        try:
            hp = int(parts[0])
        except ValueError:
            await matcher.finish("用法: /character create ghost [HP]")

    game_id = get_game_id()
    user_id = await get_dg_user_id(event)
    client = get_client()

    # Fetch active character to get origin patient info
    char_data = await client.get_active_character(game_id, user_id)
    patient = char_data.get("patient") or char_data.get("active_patient") or {}
    patient_id = patient.get("patient_id", patient.get("id", ""))
    patient_name = patient.get("name", "")
    soul_color = patient.get("soul_color", "")
    if not patient_id:
        await matcher.finish("你当前没有活跃的患者角色，请先创建患者。")

    data = await client.create_ghost(
        game_id, f"{patient_name}的幽灵", soul_color,
        origin_patient_id=patient_id,
        creator_user_id=user_id,
        initial_hp=hp,
    )
    ghost_name = data.get("name", "")
    ghost_id = data.get("id", "")
    await matcher.finish(f"幽灵角色创建成功！\n名称: {ghost_name}\nid: {ghost_id}\n等待DM分配后由对方玩家设定详细信息。")



# ── /abilities ─────────────────────────────────────────────

abilities_cmd = on_command("abilities", priority=10, block=True)


@abilities_cmd.handle()
async def handle_abilities(
    matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()
) -> None:
    try:
        game_id = get_game_id()
        target = await resolve_player_target(args, get_plain_args(args))
        user_id = target if target else await get_dg_user_id(event)

        client = get_client()
        char_data = await client.get_active_character(game_id, user_id)
        ghost = char_data.get("ghost") or char_data.get("active_ghost") or {}
        ghost_id = ghost.get("ghost_id", ghost.get("id", ""))
        if not ghost_id:
            await matcher.finish("当前没有活跃的幽灵角色。")

        data = await client.get_abilities(ghost_id, game_id=game_id)
        await matcher.finish(format_abilities(data))
    except DgCoreError as e:
        await matcher.finish(format_api_error(e))
    except Exception as e:
        msg = format_context_error(e)
        if msg:
            await matcher.finish(msg)
        raise
