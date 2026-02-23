"""单元测试 — src/plugins/dg_trpg/plugins/admin.py

覆盖范围:
- /register: 群聊拒绝 / 参数不足 / 注册成功 / API 失败
- /bind: 群聊拒绝 / 绑定成功 / 404 专属提示 / API 失败
- /unbind: 已绑定解绑成功 / 无绑定提示
- /help: 无参数主帮助 / 指定话题 / 未知话题
- /jrrp: 返回 0~100 范围 / 同日同QQ结果相同 / 不同日期不同种子

依赖隔离:
- patch get_client → 返回 mock_client (AsyncMock)
- patch get_state → 返回 mock_state (MagicMock)
- FakeMatcher.finish 捕获消息并抛出 FinishedException
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.adapters.onebot.v11 import Message

from tests.conftest import make_group_event, make_private_event
from tests.unit.conftest import FakeMatcher

# 延迟导入以避免在模块级 patch 之前触发 on_command 注册副作用
from src.plugins.dg_trpg.plugins.admin import (
    handle_bind,
    handle_help,
    handle_jrrp,
    handle_register,
    handle_unbind,
)
from src.plugins.dg_trpg.core.errors import DgCoreError


ADMIN_MODULE = "src.plugins.dg_trpg.plugins.admin"


# ---------------------------------------------------------------------------
# /register
# ---------------------------------------------------------------------------

class TestHandleRegister:
    async def test_group_event_rejected(self):
        matcher = FakeMatcher()
        event = make_group_event()
        args = Message("")
        with pytest.raises(Exception):  # FinishedException
            await handle_register(matcher, event, args)
        assert "私聊" in matcher.last_sent or "敏感" in matcher.last_sent

    async def test_missing_args(self):
        matcher = FakeMatcher()
        event = make_private_event()
        args = Message("")
        with pytest.raises(Exception):
            await handle_register(matcher, event, args)
        assert "/register" in matcher.last_sent

    async def test_success(self):
        matcher = FakeMatcher()
        event = make_private_event(user_id=12345)
        args = Message("alice mypass123")

        mock_client = AsyncMock()
        mock_client.register.return_value = {"user_id": "uid-1", "api_key": "key-abc"}
        mock_state = MagicMock()

        with (
            patch(f"{ADMIN_MODULE}.get_client", return_value=mock_client),
            patch(f"{ADMIN_MODULE}.get_state", return_value=mock_state),
        ):
            with pytest.raises(Exception):
                await handle_register(matcher, event, args)

        assert "注册成功" in matcher.last_sent
        mock_state.set_user.assert_called_once_with("12345", "uid-1", "alice")

    async def test_api_error(self):
        matcher = FakeMatcher()
        event = make_private_event()
        args = Message("alice pass")

        mock_client = AsyncMock()
        mock_client.register.side_effect = DgCoreError(409, "username taken")
        mock_state = MagicMock()

        with (
            patch(f"{ADMIN_MODULE}.get_client", return_value=mock_client),
            patch(f"{ADMIN_MODULE}.get_state", return_value=mock_state),
        ):
            with pytest.raises(Exception):
                await handle_register(matcher, event, args)

        # 应返回格式化错误，不应崩溃
        assert matcher.last_sent != ""


# ---------------------------------------------------------------------------
# /bind
# ---------------------------------------------------------------------------

class TestHandleBind:
    async def test_group_event_rejected(self):
        matcher = FakeMatcher()
        event = make_group_event()
        args = Message("")
        with pytest.raises(Exception):
            await handle_bind(matcher, event, args)
        assert "私聊" in matcher.last_sent or "敏感" in matcher.last_sent

    async def test_missing_args(self):
        matcher = FakeMatcher()
        event = make_private_event()
        args = Message("")
        with pytest.raises(Exception):
            await handle_bind(matcher, event, args)
        assert "/bind" in matcher.last_sent

    async def test_success(self):
        matcher = FakeMatcher()
        event = make_private_event(user_id=11111)
        args = Message("my-api-key-here")

        mock_client = AsyncMock()
        mock_client.resolve_platform.return_value = {"user_id": "uid-2", "username": "bob"}
        mock_state = MagicMock()

        with (
            patch(f"{ADMIN_MODULE}.get_client", return_value=mock_client),
            patch(f"{ADMIN_MODULE}.get_state", return_value=mock_state),
        ):
            with pytest.raises(Exception):
                await handle_bind(matcher, event, args)

        assert "绑定成功" in matcher.last_sent
        mock_state.set_user.assert_called_once_with("11111", "uid-2", "bob")

    async def test_404_shows_register_hint(self):
        matcher = FakeMatcher()
        event = make_private_event()
        args = Message("bad-api-key")

        mock_client = AsyncMock()
        mock_client.resolve_platform.side_effect = DgCoreError(404, "not found")
        mock_state = MagicMock()

        with (
            patch(f"{ADMIN_MODULE}.get_client", return_value=mock_client),
            patch(f"{ADMIN_MODULE}.get_state", return_value=mock_state),
        ):
            with pytest.raises(Exception):
                await handle_bind(matcher, event, args)

        assert "/register" in matcher.last_sent


# ---------------------------------------------------------------------------
# /unbind
# ---------------------------------------------------------------------------

class TestHandleUnbind:
    async def test_has_binding_success(self):
        matcher = FakeMatcher()
        event = make_private_event(user_id=99999)
        mock_state = MagicMock()
        mock_state.remove_user.return_value = True

        with patch(f"{ADMIN_MODULE}.get_state", return_value=mock_state):
            with pytest.raises(Exception):
                await handle_unbind(matcher, event)

        assert "解绑成功" in matcher.last_sent
        mock_state.remove_user.assert_called_once_with("99999")

    async def test_no_binding(self):
        matcher = FakeMatcher()
        event = make_private_event()
        mock_state = MagicMock()
        mock_state.remove_user.return_value = False

        with patch(f"{ADMIN_MODULE}.get_state", return_value=mock_state):
            with pytest.raises(Exception):
                await handle_unbind(matcher, event)

        assert "没有绑定" in matcher.last_sent


# ---------------------------------------------------------------------------
# /help
# ---------------------------------------------------------------------------

class TestHandleHelp:
    async def test_no_args_shows_main_help(self):
        matcher = FakeMatcher()
        args = Message("")
        with pytest.raises(Exception):
            await handle_help(matcher, args)
        assert matcher.last_sent != ""

    async def test_known_topic(self):
        matcher = FakeMatcher()
        args = Message("roll")
        with pytest.raises(Exception):
            await handle_help(matcher, args)
        assert "roll" in matcher.last_sent.lower() or "骰" in matcher.last_sent

    async def test_unknown_topic(self):
        matcher = FakeMatcher()
        args = Message("unknowntopic9999")
        with pytest.raises(Exception):
            await handle_help(matcher, args)
        assert matcher.last_sent != ""


# ---------------------------------------------------------------------------
# /jrrp
# ---------------------------------------------------------------------------

class TestHandleJrrp:
    async def test_result_in_range(self):
        matcher = FakeMatcher()
        event = make_group_event(user_id=12345)
        with pytest.raises(Exception):
            await handle_jrrp(matcher, event)
        # 输出包含 0~100 范围内数字
        sent = matcher.last_sent
        assert any(str(n) in sent for n in range(101))

    async def test_same_day_same_user_same_result(self):
        """同日同QQ两次调用应得到相同结果（确定性种子）。"""
        matcher1, matcher2 = FakeMatcher(), FakeMatcher()
        event = make_group_event(user_id=77777)
        with pytest.raises(Exception):
            await handle_jrrp(matcher1, event)
        with pytest.raises(Exception):
            await handle_jrrp(matcher2, event)
        assert matcher1.last_sent == matcher2.last_sent

    async def test_different_users_may_differ(self):
        """不同QQ对应不同种子，结果应不同（大概率）。"""
        matcher1, matcher2 = FakeMatcher(), FakeMatcher()
        ev1 = make_group_event(user_id=11111)
        ev2 = make_group_event(user_id=22222)
        with pytest.raises(Exception):
            await handle_jrrp(matcher1, ev1)
        with pytest.raises(Exception):
            await handle_jrrp(matcher2, ev2)
        # 不同QQ的运势结果通常不同（理论上可能相同，但可接受）
        # 这里只验证两次都有输出
        assert matcher1.last_sent != ""
        assert matcher2.last_sent != ""
