from __future__ import annotations

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from ..core.api_client import get_client
from ..core.context import get_dg_user_id, get_game_id, get_qq_uid
from ..core.errors import DgCoreError, format_api_error, format_context_error
from ..core.formatters import format_roll

# ── /roll ──────────────────────────────────────────────────

roll_cmd = on_command("roll", aliases={"r"}, priority=10, block=True)


@roll_cmd.handle()
async def handle_roll(
    matcher: Matcher, event: GroupMessageEvent, args: Message = CommandArg()
) -> None:
    expression = args.extract_plain_text().strip()
    if not expression:
        await matcher.finish("用法: /roll <骰子表达式>\n例: /roll 2d6+3, /roll d100, /roll c+2")

    try:
        client = get_client()
        game_id = ""
        user_id = ""
        try:
            game_id = get_game_id()
        except Exception:
            pass
        try:
            user_id = await get_dg_user_id(event)
        except Exception:
            pass

        data = await client.roll_dice(expression, game_id=game_id, user_id=user_id)
        await matcher.finish(format_roll(data))
    except DgCoreError as e:
        await matcher.finish(format_api_error(e))
    except Exception as e:
        msg = format_context_error(e)
        if msg:
            await matcher.finish(msg)
        raise
