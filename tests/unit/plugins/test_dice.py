"""单元测试 — src/plugins/dg_trpg/plugins/dice.py

覆盖范围:
- /roll 基本骰点（成功路径）
- /roll 空参数 → 用法提示
- /roll API 失败 → format_api_error
- /roll 无 game_id / user_id 时仍可骰点（降级为 guest 模式）
- /roll 上下文错误（NeedRegistration 等）

依赖隔离:
- patch get_client → mock_client
- patch get_game_id → 返回 "test-game" 或抛出 GameNotConfigured
- patch get_dg_user_id → 返回 "uid-1" 或抛出 NeedRegistration
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.adapters.onebot.v11 import Message

from tests.conftest import make_group_event
from tests.unit.conftest import FakeMatcher

from src.plugins.dg_trpg.core.errors import DgCoreError, GameNotConfigured, NeedRegistration
from src.plugins.dg_trpg.plugins.dice import handle_roll

DICE_MODULE = "src.plugins.dg_trpg.plugins.dice"


# ---------------------------------------------------------------------------
# /roll
# ---------------------------------------------------------------------------

class TestHandleRoll:
    async def test_no_args_shows_usage(self):
        matcher = FakeMatcher()
        event = make_group_event()
        args = Message("")
        # 直接调用（无需 patch，空参数在到达 API 调用前就 finish）
        with pytest.raises(Exception):
            await handle_roll(matcher, event, args)
        assert "/roll" in matcher.last_sent

    async def test_basic_roll_success(self):
        matcher = FakeMatcher()
        event = make_group_event(user_id=12345)
        args = Message("2d6+3")

        mock_client = AsyncMock()
        mock_client.roll_dice.return_value = {
            "expression": "2d6+3",
            "results": [3, 4],
            "total": 10,
        }

        with (
            patch(f"{DICE_MODULE}.get_client", return_value=mock_client),
            patch(f"{DICE_MODULE}.get_game_id", return_value="game-1"),
            patch(f"{DICE_MODULE}.get_dg_user_id", return_value="uid-1"),
        ):
            with pytest.raises(Exception):
                await handle_roll(matcher, event, args)

        assert "🎲" in matcher.last_sent
        assert "10" in matcher.last_sent
        mock_client.roll_dice.assert_called_once_with(
            "2d6+3", game_id="game-1", user_id="uid-1"
        )

    async def test_api_error_formats_message(self):
        matcher = FakeMatcher()
        event = make_group_event()
        args = Message("invalid??")

        mock_client = AsyncMock()
        mock_client.roll_dice.side_effect = DgCoreError(400, "invalid dice expression")

        with (
            patch(f"{DICE_MODULE}.get_client", return_value=mock_client),
            patch(f"{DICE_MODULE}.get_game_id", return_value="g-1"),
            patch(f"{DICE_MODULE}.get_dg_user_id", return_value="uid-1"),
        ):
            with pytest.raises(Exception):
                await handle_roll(matcher, event, args)

        # 应显示格式化的错误消息，不应崩溃
        assert matcher.last_sent != ""

    async def test_no_game_id_still_rolls(self):
        """game_id 未配置时应降级为空 game_id，不应中断骰点。"""
        matcher = FakeMatcher()
        event = make_group_event()
        args = Message("d6")

        mock_client = AsyncMock()
        mock_client.roll_dice.return_value = {"expression": "d6", "results": [4], "total": 4}

        with (
            patch(f"{DICE_MODULE}.get_client", return_value=mock_client),
            patch(f"{DICE_MODULE}.get_game_id", side_effect=GameNotConfigured()),
            patch(f"{DICE_MODULE}.get_dg_user_id", return_value="uid-1"),
        ):
            with pytest.raises(Exception):
                await handle_roll(matcher, event, args)

        # game_id / user_id 降级为空串时仍然调用
        call_kwargs = mock_client.roll_dice.call_args
        assert call_kwargs is not None

    async def test_no_user_still_rolls(self):
        """用户未注册时 user_id 降级为空串，不应中断骰点。"""
        matcher = FakeMatcher()
        event = make_group_event()
        args = Message("d100")

        mock_client = AsyncMock()
        mock_client.roll_dice.return_value = {"expression": "d100", "total": 55}

        with (
            patch(f"{DICE_MODULE}.get_client", return_value=mock_client),
            patch(f"{DICE_MODULE}.get_game_id", return_value="g-1"),
            patch(f"{DICE_MODULE}.get_dg_user_id", side_effect=NeedRegistration("12345")),
        ):
            with pytest.raises(Exception):
                await handle_roll(matcher, event, args)

        # 即使未注册也应该能骰点
        mock_client.roll_dice.assert_called_once()
