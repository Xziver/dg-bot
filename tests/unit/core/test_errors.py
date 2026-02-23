"""单元测试 — src/plugins/dg_trpg/core/errors.py

覆盖范围:
- 所有异常类的构造与属性
- format_api_error: 各 HTTP 状态码映射、detail 附加规则
- format_context_error: 各上下文异常 → 提示字符串
"""
from __future__ import annotations

import pytest

from src.plugins.dg_trpg.core.errors import (
    DgCoreError,
    GameNotConfigured,
    InsufficientPermission,
    LocationNotBound,
    NeedRegistration,
    NoActiveSession,
    RegionNotBound,
    StaleCacheError,
    format_api_error,
    format_context_error,
)


# ---------------------------------------------------------------------------
# DgCoreError
# ---------------------------------------------------------------------------

class TestDgCoreError:
    def test_attributes(self):
        err = DgCoreError(404, "not found")
        assert err.status_code == 404
        assert err.detail == "not found"

    def test_empty_detail(self):
        err = DgCoreError(500)
        assert err.detail == ""
        assert "500" in str(err)

    def test_is_exception(self):
        assert isinstance(DgCoreError(400), Exception)


# ---------------------------------------------------------------------------
# NeedRegistration
# ---------------------------------------------------------------------------

class TestNeedRegistration:
    def test_default_is_not_target(self):
        err = NeedRegistration("12345")
        assert err.qq_uid == "12345"
        assert err.is_target is False

    def test_is_target_flag(self):
        err = NeedRegistration("99999", is_target=True)
        assert err.is_target is True


# ---------------------------------------------------------------------------
# RegionNotBound / LocationNotBound / NoActiveSession
# ---------------------------------------------------------------------------

class TestContextExceptions:
    def test_region_not_bound_group_id(self):
        err = RegionNotBound("group-42")
        assert err.group_id == "group-42"

    def test_location_not_bound_group_id(self):
        err = LocationNotBound("group-42")
        assert err.group_id == "group-42"

    def test_no_active_session_group_id(self):
        err = NoActiveSession("group-7")
        assert err.group_id == "group-7"

    def test_game_not_configured(self):
        err = GameNotConfigured()
        assert isinstance(err, Exception)

    def test_stale_cache_error_attrs(self):
        err = StaleCacheError("user", "uid-404 gone")
        assert err.cache_type == "user"
        assert "uid-404" in err.detail

    def test_insufficient_permission_default(self):
        err = InsufficientPermission()
        assert "权限" in err.detail

    def test_insufficient_permission_custom(self):
        err = InsufficientPermission("仅DM可用")
        assert err.detail == "仅DM可用"


# ---------------------------------------------------------------------------
# format_api_error
# ---------------------------------------------------------------------------

class TestFormatApiError:
    @pytest.mark.parametrize(
        ("status_code", "expected_fragment"),
        [
            (400, "操作失败"),
            (401, "Bot认证失败"),
            (403, "权限不足"),
            (404, "未找到"),
            (422, "参数错误"),
            (500, "服务器错误"),
        ],
    )
    def test_known_status_codes(self, status_code: int, expected_fragment: str):
        msg = format_api_error(DgCoreError(status_code))
        assert expected_fragment in msg

    def test_unknown_status_code_fallback(self):
        msg = format_api_error(DgCoreError(418, "I'm a teapot"))
        assert "418" in msg

    def test_detail_appended_for_400(self):
        msg = format_api_error(DgCoreError(400, "字段缺失"))
        assert "字段缺失" in msg

    def test_detail_not_appended_for_401(self):
        """401 属于 Bot 配置错误，不对外暴露 detail。"""
        msg = format_api_error(DgCoreError(401, "bad key"))
        assert "bad key" not in msg

    def test_detail_not_appended_for_500(self):
        """500 服务器错误，不暴露 detail。"""
        msg = format_api_error(DgCoreError(500, "stack trace"))
        assert "stack trace" not in msg


# ---------------------------------------------------------------------------
# format_context_error
# ---------------------------------------------------------------------------

class TestFormatContextError:
    def test_need_registration_self(self):
        msg = format_context_error(NeedRegistration("12345"))
        assert msg is not None
        assert "注册" in msg
        assert "register" in msg.lower() or "/register" in msg

    def test_need_registration_target(self):
        msg = format_context_error(NeedRegistration("99999", is_target=True))
        assert msg is not None
        assert "99999" in msg
        assert "未注册" in msg

    def test_region_not_bound(self):
        msg = format_context_error(RegionNotBound("g-1"))
        assert msg is not None
        assert "区域" in msg

    def test_location_not_bound(self):
        msg = format_context_error(LocationNotBound("g-1"))
        assert msg is not None
        assert "地点" in msg

    def test_no_active_session(self):
        msg = format_context_error(NoActiveSession("g-1"))
        assert msg is not None
        assert "场次" in msg

    def test_game_not_configured(self):
        msg = format_context_error(GameNotConfigured())
        assert msg is not None

    def test_unknown_exception_returns_none(self):
        msg = format_context_error(ValueError("unexpected"))
        assert msg is None
