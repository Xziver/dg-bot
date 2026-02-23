"""Root conftest: 在 pytest 收集阶段（模块级）初始化 NoneBot 环境。

模块级初始化确保所有插件模块在被导入前（on_command 注册前）
NoneBot 已经处于就绪状态，避免"NoneBot not initialized"错误。
"""
from __future__ import annotations

import os

import pytest

# ---------------------------------------------------------------------------
# NoneBot 模块级初始化（在 pytest 收集 conftest 时执行，早于任何测试模块导入）
# ---------------------------------------------------------------------------

os.environ.setdefault("DRIVER", "~none")
os.environ.setdefault("DG_CORE_URL", "http://test.local")
os.environ.setdefault("DG_BOT_API_KEY", "test-api-key")
os.environ.setdefault("DG_GAME_ID", "test-game-id")

import nonebot  # noqa: E402
from nonebot.adapters.onebot.v11 import Adapter as OneBotAdapter  # noqa: E402

nonebot.init(
    driver="~none",
    dg_core_url="http://test.local",
    dg_bot_api_key="test-api-key",
    dg_game_id="test-game-id",
)
nonebot.get_driver().register_adapter(OneBotAdapter)


# ---------------------------------------------------------------------------
# 通用 OneBot V11 事件构造辅助
# ---------------------------------------------------------------------------

def make_group_event(
    *,
    user_id: int = 123_456_789,
    group_id: int = 987_654_321,
    text: str = "",
):
    """构造一个 GroupMessageEvent，用于 handler 单元测试。"""
    from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message

    return GroupMessageEvent(
        time=1_700_000_000,
        self_id=100_000_001,
        post_type="message",
        sub_type="normal",
        user_id=user_id,
        group_id=group_id,
        message_id=1,
        message=Message(text),
        raw_message=text,
        font=0,
        sender={"user_id": user_id, "nickname": "TestUser", "role": "member"},
        message_type="group",
    )


def make_private_event(
    *,
    user_id: int = 123_456_789,
    text: str = "",
):
    """构造一个私聊 MessageEvent，用于 handler 单元测试。"""
    from nonebot.adapters.onebot.v11 import Message, PrivateMessageEvent

    return PrivateMessageEvent(
        time=1_700_000_000,
        self_id=100_000_001,
        post_type="message",
        sub_type="friend",
        user_id=user_id,
        message_id=1,
        message=Message(text),
        raw_message=text,
        font=0,
        sender={"user_id": user_id, "nickname": "TestUser"},
        message_type="private",
    )
