from __future__ import annotations

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..core.api_client import get_client
from ..core.context import get_dg_user_id, get_game_id, get_group_id, get_plain_args
from ..core.errors import DgCoreError, format_api_error, format_context_error
from ..core.formatters import format_location_list, format_region_list
from ..core.state import get_state

# ── /region ────────────────────────────────────────────────

region_cmd = on_command("region", priority=10, block=True)


@region_cmd.handle()
async def handle_region(
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
            "locations": _locations,
            "bind": _bind,
            "unbind": _unbind,
        }
        handler = handlers.get(subcmd)
        if handler:
            await handler(matcher, event, sub_args)
        else:
            await matcher.finish(
                f"未知子命令: {subcmd}\n"
                "用法: /region [add|list|locations|bind|unbind]"
            )
    except DgCoreError as e:
        await matcher.finish(format_api_error(e))
    except Exception as e:
        msg = format_context_error(e)
        if msg:
            await matcher.finish(msg)
        raise


async def _add(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    parts = sub_args.split(maxsplit=1)
    if len(parts) < 2:
        await matcher.finish("用法: /region add <区域代码> <区域名称>\n例: /region add A 数据荒原")

    code = parts[0]
    name = parts[1]
    game_id = get_game_id()
    user_id = await get_dg_user_id(event)

    client = get_client()
    await client.create_region(game_id, code, name, user_id=user_id)
    await matcher.finish(f"区域创建成功！[{code}] {name}")


async def _edit(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    await matcher.finish("功能暂未开放：区域编辑需要后端API支持。")


async def _delete(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    await matcher.finish("功能暂未开放：区域删除需要后端API支持。")


async def _list(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    game_id = get_game_id()
    client = get_client()
    data = await client.list_regions(game_id)
    await matcher.finish(format_region_list(data))


async def _locations(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    game_id = get_game_id()
    client = get_client()

    if sub_args.strip():
        # Find region by name/code
        region_name = sub_args.strip()
        regions = await client.list_regions(game_id)
        region_id = None
        for r in regions:
            if r.get("name") == region_name or r.get("code") == region_name or r.get("id") == region_name:
                region_id = r.get("id")
                break
        if not region_id:
            await matcher.finish(f"未找到区域 '{region_name}'。")
            return
    else:
        # Use bound region
        group_id = get_group_id(event)
        region = get_state().get_region(group_id)
        if not region:
            await matcher.finish("请指定区域名称，或先使用 /region bind 绑定区域。")
            return
        region_id = region["region_id"]

    data = await client.list_locations(game_id, region_id)
    await matcher.finish(format_location_list(data))


async def _bind(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    if not sub_args:
        await matcher.finish("用法: /region bind <区域代码>\n例: /region bind A")

    region_code = sub_args.strip()
    game_id = get_game_id()
    group_id = get_group_id(event)

    # Verify region exists
    client = get_client()
    regions = await client.list_regions(game_id)
    target = None
    for r in regions:
        if r.get("code") == region_code or r.get("name") == region_code or r.get("id") == region_code:
            target = r
            break

    if not target:
        await matcher.finish(f"区域 '{region_code}' 不存在，请先添加该区域后再绑定！")

    region_id = target.get("id", "")
    region_name = target.get("name", region_code)
    code = target.get("code", region_code)

    get_state().set_region(group_id, region_id, code, region_name)
    await matcher.finish(f"本群已绑定到区域: [{code}] {region_name}")


async def _unbind(matcher: Matcher, event: GroupMessageEvent, sub_args: str) -> None:
    group_id = get_group_id(event)
    removed = get_state().remove_region(group_id)
    if removed:
        await matcher.finish("区域解绑成功！")
    else:
        await matcher.finish("本群当前没有绑定任何区域。")
