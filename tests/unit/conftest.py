"""Unit test conftest: 为所有单元测试提供通用 mock fixtures。"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# FakeMatcher — 捕获 matcher.finish 的消息，并抛出 FinishedException
# ---------------------------------------------------------------------------

class FakeMatcher:
    """替代真实 Matcher，将 finish() 发送的消息记录到 sent 列表。"""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def finish(self, msg: Any = "", **kwargs: Any) -> None:
        from nonebot.exception import FinishedException

        self.sent.append(str(msg))
        raise FinishedException()

    @property
    def last_sent(self) -> str:
        """返回最后一次 finish 发送的消息。"""
        return self.sent[-1] if self.sent else ""


@pytest.fixture
def fake_matcher() -> FakeMatcher:
    """返回一个 FakeMatcher 实例。"""
    return FakeMatcher()


# ---------------------------------------------------------------------------
# mock_client — 预配置好常用返回值的 DgCoreClient mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client() -> AsyncMock:
    """返回一个 AsyncMock DgCoreClient，可在测试中覆盖具体方法返回值。"""
    client = AsyncMock()

    # 默认返回值（可在各测试中覆盖）
    client.register.return_value = {"user_id": "uid-001", "api_key": "key-abc"}
    client.resolve_platform.return_value = {"user_id": "uid-001", "username": "testuser"}
    client.roll_dice.return_value = {
        "expression": "2d6",
        "results": [3, 4],
        "total": 7,
    }
    client.submit_event.return_value = {
        "success": True,
        "event_type": "event_check",
        "data": {},
        "narrative": "操作成功",
        "state_changes": [],
        "rolls": [],
    }
    client.get_active_character.return_value = {
        "patient": {"id": "pat-1", "name": "小明", "soul_color": "C"},
        "ghost": {
            "id": "ghost-1",
            "name": "影子",
            "hp": 10,
            "max_hp": 10,
            "mp": 5,
            "max_mp": 5,
            "cmyk": {"C": 3, "M": 0, "Y": 0, "K": 0},
            "abilities": [],
            "buffs": [],
        },
    }
    client.list_buffs.return_value = []
    client.list_regions.return_value = []
    client.list_locations.return_value = []
    client.list_characters.return_value = []
    client.get_session_info.return_value = {
        "session_id": "sess-1",
        "location_name": "诊室",
        "status": "active",
        "players": [],
    }
    return client


# ---------------------------------------------------------------------------
# mock_state — 预配置的 StateManager mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_state() -> MagicMock:
    """返回一个 MagicMock StateManager，带常用默认返回值。"""
    state = MagicMock()
    state.get_user.return_value = {"user_id": "uid-001", "username": "testuser"}
    state.get_region.return_value = {
        "region_id": "region-1",
        "region_code": "R01",
        "region_name": "测试区域",
    }
    state.get_location.return_value = {
        "location_id": "loc-1",
        "location_name": "测试地点",
    }
    state.get_session.return_value = "sess-1"
    state.get_last_event_check.return_value = None
    state.remove_user.return_value = True
    state.remove_region.return_value = True
    return state
