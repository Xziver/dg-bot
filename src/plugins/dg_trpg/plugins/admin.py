from __future__ import annotations

import hashlib
from datetime import date

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..core.api_client import get_client
from ..core.context import get_qq_uid
from ..core.errors import DgCoreError, format_api_error
from ..core.state import get_state

PRIVATE_ONLY_MSG = "⚠ 该命令包含敏感信息，请私聊Bot使用。"

# ── /register ──────────────────────────────────────────────

register_cmd = on_command("register", priority=10, block=True)


@register_cmd.handle()
async def handle_register(
    matcher: Matcher, event: MessageEvent, args: Message = CommandArg()
) -> None:
    if isinstance(event, GroupMessageEvent):
        await matcher.finish(PRIVATE_ONLY_MSG)

    text = args.extract_plain_text().strip()
    parts = text.split()
    if len(parts) < 2:
        await matcher.finish("用法: /register <用户名> <密码>\n例: /register player1 mypass123")

    username, password = parts[0], parts[1]
    qq_uid = get_qq_uid(event)

    try:
        client = get_client()
        data = await client.register(username, password, platform="qq", platform_uid=qq_uid)
        user_id = data.get("user_id", "")
        api_key = data.get("api_key", "")

        if user_id:
            get_state().set_user(qq_uid, user_id, username)

        msg = f"注册成功！\n用户名: {username}"
        if api_key:
            msg += f"\nAPI Key: {api_key}\n请妥善保管你的API Key，可用于 /bind 重新绑定账号。"
        await matcher.finish(msg)
    except DgCoreError as e:
        await matcher.finish(format_api_error(e))


# ── /bind ──────────────────────────────────────────────────

bind_cmd = on_command("bind", priority=10, block=True)


@bind_cmd.handle()
async def handle_bind(
    matcher: Matcher, event: MessageEvent, args: Message = CommandArg()
) -> None:
    if isinstance(event, GroupMessageEvent):
        await matcher.finish(PRIVATE_ONLY_MSG)

    text = args.extract_plain_text().strip()
    if not text:
        await matcher.finish("用法: /bind <api_key>\n例: /bind your-api-key-here")

    api_key = text.split()[0]
    qq_uid = get_qq_uid(event)

    try:
        client = get_client()
        data = await client.resolve_platform("qq", qq_uid)
        user_id = data.get("user_id", "")
        username = data.get("username", "")

        if user_id:
            get_state().set_user(qq_uid, user_id, username)
            await matcher.finish(f"账号绑定成功！\n用户名: {username}")
        else:
            await matcher.finish("绑定失败：无法找到关联账号。请确认API Key是否正确。")
    except DgCoreError as e:
        if e.status_code == 404:
            await matcher.finish(
                "绑定失败：未找到关联账号。\n请先使用 /register <用户名> <密码> 注册账号。"
            )
        await matcher.finish(format_api_error(e))


# ── /unbind ────────────────────────────────────────────────

unbind_cmd = on_command("unbind", priority=10, block=True)


@unbind_cmd.handle()
async def handle_unbind(matcher: Matcher, event: MessageEvent) -> None:
    qq_uid = get_qq_uid(event)
    removed = get_state().remove_user(qq_uid)
    if removed:
        await matcher.finish("账号解绑成功！请使用 /bind <api_key> 重新绑定账号以继续使用角色相关功能。")
    else:
        await matcher.finish("你当前没有绑定任何账号。")


# ── /help ──────────────────────────────────────────────────

help_cmd = on_command("help", priority=10, block=True)

HELP_TOPICS: dict[str, str] = {
    "register": "注册账号（私聊Bot使用）\n用法: /register <用户名> <密码>\n注册成功后自动绑定QQ号，并返回api_key。",
    "bind": "绑定账号（私聊Bot使用）\n用法: /bind <api_key>\n登录后自动绑定QQ号。",
    "unbind": "解绑账号\n用法: /unbind\n解绑后需重新登录才能使用角色相关功能。",
    "game": (
        "游戏管理\n"
        "/game join [PL|DM] - 加入游戏\n"
        "/game role <PL|DM> - 切换身份\n"
        "/game info - 查看游戏信息\n"
        "/game add @玩家 [PL|DM] - 添加玩家到游戏 (DM)"
    ),
    "character": (
        "角色管理\n"
        "/character show - 显示当前角色信息\n"
        "/character list - 显示角色列表\n"
        "/character switch <名称|ID> - 切换角色\n"
        "/character set <属性> <值> - 修改属性 (DM)\n"
        "/character delete <名称|ID> - 删除角色\n"
        "/character move <地点> - 移动到地点\n"
        "/character create patient <名称> <颜色> [性别] [年龄] [身份] - 创建患者\n"
        "/character create ghost <名称> <颜色> [HP] - 创建幽灵 (DM)\n"
        "/character assign <幽灵> @玩家 - 分配同伴 (DM)"
    ),
    "roll": "骰点\n用法: /roll <骰子表达式>\n例: /roll 2d6+3, /roll d100, /roll c+2",
    "buff": (
        "BUFF管理\n"
        "/buff add <名称> <表达式> [回合数] - 添加BUFF (DM)\n"
        "/buff show - 查看BUFF列表\n"
        "/buff remove <名称> - 移除BUFF (DM)"
    ),
    "com": (
        "通信\n"
        "/com <@对方|角色名> - 发起通信请求\n"
        "/com list - 查看通信请求\n"
        "/com accept <对方|ID> [能力] - 接受通信\n"
        "/com reject <对方|ID> - 拒绝通信\n"
        "/com cancel <对方|ID> - 取消通信"
    ),
    "event": (
        "事件检定\n"
        "/event set <名称> <表达式> [颜色] - 设定事件 (DM)\n"
        "/event check <名称> [颜色] - 进行检定\n"
        "/event list - 查看事件列表\n"
        "/event delete <名称> - 删除事件 (DM)"
    ),
    "re": "同色重投\n用法: /re <打印能力名称>\n使用与检定相同颜色的打印能力重投。",
    "hre": "异色重投\n用法: /hre <打印能力名称>\n使用任意颜色打印能力重投，消耗1MP。",
    "item": (
        "道具管理\n"
        "/item list - 查看道具列表\n"
        "/item use <名称> - 使用道具\n"
        "/item grant <名称> [数量] [@目标] - 发放道具 (DM)\n"
        "/item create <名称> [描述] [效果] - 创建道具 (DM)"
    ),
    "inventory": "查看背包\n用法: /inventory [@玩家]",
    "abilities": "查看打印能力\n用法: /abilities",
    "session": (
        "场次管理\n"
        "/session start - 开始场次 (DM)\n"
        "/session end - 结束场次 (DM)\n"
        "/session pause - 暂停场次 (DM)\n"
        "/session resume - 恢复场次 (DM)\n"
        "/session info - 查看场次信息\n"
        "/session add <@玩家|名称> - 添加玩家 (DM)\n"
        "/session remove <@玩家|名称> - 移除玩家 (DM)"
    ),
    "region": (
        "区域管理\n"
        "/region add <代码> <名称> - 添加区域 (DM)\n"
        "/region list - 查看区域列表\n"
        "/region locations [名称] - 查看区域地点\n"
        "/region bind <代码> - 绑定群聊到区域 (DM)\n"
        "/region unbind - 解绑区域 (DM)"
    ),
    "location": (
        "地点管理\n"
        "/location add <区域> <名称> [描述] - 添加地点 (DM)\n"
        "/location list - 查看地点列表\n"
        "/location players [名称] - 查看地点玩家\n"
        "/location bind <名称> - 绑定群聊到地点 (DM)\n"
        "/location unbind - 解绑地点 (DM)"
    ),
    "timeline": (
        "时间线\n"
        "/timeline info [数量] - 查看时间线\n"
        "/timeline export - 导出时间线\n"
        "/timeline game [数量] - 查看游戏时间线"
    ),
    "jrrp": "今日运势\n用法: /jrrp\n查询今日运势值(0-100)。",
    "cache": (
        "缓存管理 (管理员)\n"
        "/cache status - 查看缓存状态\n"
        "/cache flush [all|user|region|location|session] - 清除缓存\n"
        "/cache validate - 重新验证缓存"
    ),
}

HELP_MAIN = (
    "【小倩 - 电子幽灵TRPG Bot 帮助】\n"
    "账号: /register /bind /unbind\n"
    "游戏: /game\n"
    "角色: /character /abilities\n"
    "骰点: /roll\n"
    "检定: /event /re /hre\n"
    "BUFF: /buff\n"
    "通信: /com\n"
    "道具: /item /inventory\n"
    "场次: /session\n"
    "区域: /region\n"
    "地点: /location\n"
    "时间线: /timeline\n"
    "管理: /cache\n"
    "其他: /help /jrrp\n"
    "\n输入 /help <命令> 查看具体用法，例如: /help roll"
)


@help_cmd.handle()
async def handle_help(matcher: Matcher, args: Message = CommandArg()) -> None:
    text = args.extract_plain_text().strip().lower()
    if not text:
        await matcher.finish(HELP_MAIN)
    topic = text.split()[0].lstrip("/")
    if topic in HELP_TOPICS:
        await matcher.finish(HELP_TOPICS[topic])
    await matcher.finish(f"未找到命令 '{topic}' 的帮助信息。\n使用 /help 查看所有可用命令。")


# ── /jrrp ──────────────────────────────────────────────────

jrrp_cmd = on_command("jrrp", priority=10, block=True)


@jrrp_cmd.handle()
async def handle_jrrp(matcher: Matcher, event: MessageEvent) -> None:
    qq_uid = get_qq_uid(event)
    today = date.today().isoformat()
    seed = f"{today}:{qq_uid}"
    value = int(hashlib.md5(seed.encode()).hexdigest(), 16) % 101

    if value >= 90:
        comment = "运势极佳！今天是被命运眷顾的一天✨"
    elif value >= 70:
        comment = "运势不错，今天适合冒险！"
    elif value >= 50:
        comment = "运势平平，稳中求进。"
    elif value >= 30:
        comment = "运势一般，小心行事。"
    elif value >= 10:
        comment = "运势较差，今天还是低调一些吧…"
    else:
        comment = "运势极差…今天可能不适合检定💀"

    await matcher.finish(f"🔮 今日运势: {value}/100\n{comment}")
