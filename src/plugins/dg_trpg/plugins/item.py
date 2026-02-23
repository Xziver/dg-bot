from __future__ import annotations

import json

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
    get_session_id,
    resolve_player_target,
)
from ..core.errors import DgCoreError, format_api_error, format_context_error
from ..core.formatters import format_engine_result, format_inventory, format_item_definitions

# ── /item ──────────────────────────────────────────────────

item_cmd = on_command("item", priority=10, block=True)


@item_cmd.handle()
async def handle_item(
    matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()
) -> None:
    text = get_plain_args(args)
    parts = text.split(maxsplit=1)
    subcmd = parts[0] if parts else "list"
    sub_args = parts[1] if len(parts) > 1 else ""

    try:
        handlers = {
            "list": _list,
            "use": _use,
            "grant": _grant,
            "create": _create,
        }
        handler = handlers.get(subcmd)
        if handler:
            await handler(matcher, event, args, sub_args)
        else:
            await matcher.finish(
                f"未知子命令: {subcmd}\n用法: /item [list|use|grant|create]"
            )
    except DgCoreError as e:
        await matcher.finish(format_api_error(e))
    except Exception as e:
        msg = format_context_error(e)
        if msg:
            await matcher.finish(msg)
        raise


async def _list(
    matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str
) -> None:
    game_id = get_game_id()
    client = get_client()
    data = await client.list_item_definitions(game_id)
    await matcher.finish(format_item_definitions(data))


async def _use(
    matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str
) -> None:
    target_user_id, remaining = await extract_target_from_args(args, sub_args)

    if not remaining:
        await matcher.finish(
            "用法: /item use [@目标] <道具名称>\n"
            "例: /item use 治疗药水\n"
            "例: /item use @玩家 治疗药水"
        )

    item_name = remaining.strip()
    game_id = get_game_id()
    sender_user_id = await get_dg_user_id(event)
    acting_user_id = target_user_id or sender_user_id

    try:
        session_id = get_session_id(event)
    except Exception:
        session_id = None

    client = get_client()
    data = await client.submit_event(
        game_id,
        session_id,
        acting_user_id,
        {"event_type": "item_use", "item_def_id": item_name},
    )
    await matcher.finish(format_engine_result(data))


async def _grant(
    matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str
) -> None:
    parts = sub_args.split()

    if not parts:
        await matcher.finish(
            "用法: /item grant <道具名称> [数量] [<@目标|QQ号|角色名>]\n"
            "例: /item grant 强壮药剂 2 @player"
        )

    item_name = parts[0]
    count = 1
    target_text: str | None = None

    for p in parts[1:]:
        try:
            count = int(p)
        except ValueError:
            target_text = p

    game_id = get_game_id()
    user_id = await get_dg_user_id(event)

    # Determine target user: @mention/QQ号/角色名, or self
    target_user_id = await resolve_player_target(args, target_text or "")
    if not target_user_id:
        target_user_id = user_id

    # Resolve target's active patient_id (v2 API requires patient_id in item_grant)
    client = get_client()
    char_data = await client.get_active_character(game_id, target_user_id)
    patient = char_data.get("patient") or char_data.get("active_patient") or {}
    patient_id = patient.get("patient_id", patient.get("id", ""))
    if not patient_id:
        await matcher.finish("目标玩家没有活跃的患者角色，无法发放道具。")
        return

    data = await client.grant_item(game_id, user_id, patient_id, item_name, count=count)

    if not data.get("success", True):
        await matcher.finish(format_engine_result(data))

    count_str = f" x{count}" if count > 1 else ""
    await matcher.finish(f"道具 {item_name}{count_str} 已发放。")


async def _create(
    matcher: Matcher, event: GroupMessageEvent, args: Message, sub_args: str
) -> None:
    if not sub_args:
        await matcher.finish(
            "用法: /item create <名称> [描述] [效果JSON]\n"
            '例: /item create 治疗药水 回复3点HP {"type":"heal_hp","value":3}'
        )

    parts = sub_args.split(maxsplit=2)
    name = parts[0]
    description = ""
    effects = None

    if len(parts) > 1:
        # Check if second part is JSON
        try:
            effects = [json.loads(parts[1])]
        except (json.JSONDecodeError, ValueError):
            description = parts[1]

    if len(parts) > 2 and effects is None:
        try:
            effects = [json.loads(parts[2])]
        except (json.JSONDecodeError, ValueError):
            pass

    game_id = get_game_id()
    user_id = await get_dg_user_id(event)

    client = get_client()
    await client.create_item_definition(
        game_id, name, description=description, effects=effects, user_id=user_id
    )
    await matcher.finish(f"道具定义创建成功！名称: {name}")


# ── /inventory ─────────────────────────────────────────────

inventory_cmd = on_command("inventory", priority=10, block=True)


@inventory_cmd.handle()
async def handle_inventory(
    matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()
) -> None:
    try:
        game_id = get_game_id()
        target = await resolve_player_target(args, get_plain_args(args))
        user_id = target if target else await get_dg_user_id(event)

        client = get_client()
        data = await client.get_inventory(game_id, user_id)
        await matcher.finish(format_inventory(data))
    except DgCoreError as e:
        await matcher.finish(format_api_error(e))
    except Exception as e:
        msg = format_context_error(e)
        if msg:
            await matcher.finish(msg)
        raise
