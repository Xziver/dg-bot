from __future__ import annotations

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..core.api_client import get_client
from ..core.context import (
    get_dg_user_id,
    get_game_id,
    get_group_id,
    get_plain_args,
    get_region_id,
)
from ..core.errors import DgCoreError, format_api_error, format_context_error
from ..core.formatters import format_location_list, format_location_players
from ..core.state import get_state

# ── /location ──────────────────────────────────────────────

location_cmd = on_command("location", priority=10, block=True)


@location_cmd.handle()
async def handle_location(
    matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()
) -> None:
    text = get_plain_args(args)
    parts = text.split(maxsplit=1)
    subcmd = parts[0] if parts else "list"
    sub_args = parts[1] if len(parts) > 1 else ""

    try:
        handlers = {
            "add": _add,
            "edit": _edit,
            "delete": _delete,
            "list": _list,
            "players": _players,
            "bind": _bind,
            "unbind": _unbind,
        }
        handler = handlers.get(subcmd)
        if handler:
            await handler(matcher, event, sub_args)
        else:
            await matcher.finish(
                f"未知子命令: {subcmd}\n"
                "用法: /location [add|list|players|bind|unbind]"
            )
    except DgCoreError as e:
        await matcher.finish(format_api_error(e))
    except Exception as e:
        msg = format_context_error(e)
        if msg:
            await matcher.finish(msg)
        raise


async def _add(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    parts = sub_args.split(maxsplit=2)
    if len(parts) < 2:
        await matcher.finish(
            "用法: /location add <所属区域> <地点名称> [描述]\n"
            "例: /location add A 酒馆 一个热闹的酒馆"
        )

    region_name = parts[0]
    loc_name = parts[1]
    description = parts[2] if len(parts) > 2 else ""

    game_id = get_game_id()
    user_id = await get_dg_user_id(event)

    # Find region ID
    client = get_client()
    regions = await client.list_regions(game_id)
    region_id = None
    for r in regions:
        if r.get("code") == region_name or r.get("name") == region_name or r.get("id") == region_name:
            region_id = r.get("id")
            break

    if not region_id:
        await matcher.finish(f"未找到区域 '{region_name}'。请先创建区域。")

    await client.create_location(region_id, loc_name, description=description, user_id=user_id)
    await matcher.finish(f"地点创建成功！{loc_name}")


async def _edit(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    await matcher.finish("功能暂未开放：地点编辑需要后端API支持。")


async def _delete(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    await matcher.finish("功能暂未开放：地点删除需要后端API支持。")


async def _list(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    group_id = get_group_id(event)
    state = get_state()

    # Try to use bound region
    region = state.get_region(group_id)
    if not region:
        try:
            region_id = get_region_id(event)
        except Exception:
            await matcher.finish("请先使用 /region bind 绑定区域。")
            return
    else:
        region_id = region["region_id"]

    client = get_client()
    data = await client.list_locations(region_id)
    await matcher.finish(format_location_list(data))


async def _players(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    if sub_args.strip():
        location_name = sub_args.strip()
        # Need to find location ID by name
        group_id = get_group_id(event)
        state = get_state()
        region = state.get_region(group_id)
        if not region:
            await matcher.finish("请先使用 /region bind 绑定区域。")
            return

        client = get_client()
        locations = await client.list_locations(region["region_id"])
        location_id = None
        for loc in locations:
            if loc.get("name") == location_name or loc.get("id") == location_name:
                location_id = loc.get("id")
                break

        if not location_id:
            await matcher.finish(f"未找到地点 '{location_name}'。")
            return
    else:
        # Use bound location
        group_id = get_group_id(event)
        location = get_state().get_location(group_id)
        if not location:
            await matcher.finish("请指定地点名称，或先使用 /location bind 绑定地点。")
            return
        location_id = location["location_id"]

    client = get_client()
    data = await client.get_location_players(location_id)
    await matcher.finish(format_location_players(data))


async def _bind(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    if not sub_args:
        await matcher.finish("用法: /location bind <地点名称>\n例: /location bind 酒馆")

    loc_name = sub_args.strip()
    group_id = get_group_id(event)

    # Find location in bound region
    state = get_state()
    region = state.get_region(group_id)
    if not region:
        await matcher.finish("请先使用 /region bind 绑定区域。")
        return

    client = get_client()
    locations = await client.list_locations(region["region_id"])
    target = None
    for loc in locations:
        if loc.get("name") == loc_name or loc.get("id") == loc_name:
            target = loc
            break

    if not target:
        await matcher.finish(f"地点 '{loc_name}' 不存在，请先添加该地点后再绑定！")

    location_id = target.get("id", "")
    location_name = target.get("name", loc_name)

    state.set_location(group_id, location_id, location_name)
    await matcher.finish(f"本群已绑定到地点: {location_name}")


async def _unbind(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    group_id = get_group_id(event)
    removed = get_state().remove_location(group_id)
    if removed:
        await matcher.finish("地点解绑成功！")
    else:
        await matcher.finish("本群当前没有绑定任何地点。")
