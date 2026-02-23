"""单元测试 — src/plugins/dg_trpg/core/state.py

覆盖范围:
- StateManager 的所有 CRUD 方法
- 文件持久化（重新构造后仍可读）
- 清除操作返回正确计数
- 内存级 last_event_check 操作

依赖隔离: 通过 monkeypatch 将 nonebot_plugin_localstore.get_data_dir
          重定向到 pytest 提供的 tmp_path，完全隔离文件 I/O。
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import src.plugins.dg_trpg.core.state as state_module
from src.plugins.dg_trpg.core.state import StateManager


# ---------------------------------------------------------------------------
# Fixture: 使用临时目录隔离的 StateManager
# ---------------------------------------------------------------------------

@pytest.fixture
def sm(tmp_path: Path) -> StateManager:
    """返回使用临时目录的 StateManager，每个测试独享。"""
    with patch.object(
        state_module.store, "get_data_dir", return_value=tmp_path
    ):
        manager = StateManager()
    return manager


@pytest.fixture
def sm_factory(tmp_path: Path):
    """工厂 fixture：多次构造同一 tmp_path 的 StateManager，用于持久化测试。"""
    def _make() -> StateManager:
        with patch.object(
            state_module.store, "get_data_dir", return_value=tmp_path
        ):
            return StateManager()
    return _make


# ---------------------------------------------------------------------------
# User cache
# ---------------------------------------------------------------------------

class TestUserCache:
    def test_set_and_get_user(self, sm: StateManager):
        sm.set_user("111", "uid-1", "alice")
        result = sm.get_user("111")
        assert result is not None
        assert result["user_id"] == "uid-1"
        assert result["username"] == "alice"

    def test_get_user_missing_returns_none(self, sm: StateManager):
        assert sm.get_user("nonexistent") is None

    def test_remove_existing_user(self, sm: StateManager):
        sm.set_user("222", "uid-2", "bob")
        removed = sm.remove_user("222")
        assert removed is True
        assert sm.get_user("222") is None

    def test_remove_nonexistent_user_returns_false(self, sm: StateManager):
        assert sm.remove_user("ghost") is False

    def test_get_all_users(self, sm: StateManager):
        sm.set_user("a", "ua", "alice")
        sm.set_user("b", "ub", "bob")
        users = sm.get_all_users()
        assert "a" in users
        assert "b" in users

    def test_clear_all_users_returns_count(self, sm: StateManager):
        sm.set_user("x", "ux", "x-user")
        sm.set_user("y", "uy", "y-user")
        count = sm.clear_all_users()
        assert count == 2
        assert sm.get_all_users() == {}

    def test_user_persistence(self, sm_factory):
        """写入后重新构造 StateManager 仍可读取。"""
        m1 = sm_factory()
        m1.set_user("persist-qq", "uid-persist", "persistent_user")

        m2 = sm_factory()
        result = m2.get_user("persist-qq")
        assert result is not None
        assert result["user_id"] == "uid-persist"


# ---------------------------------------------------------------------------
# Region cache
# ---------------------------------------------------------------------------

class TestRegionCache:
    def test_set_and_get_region(self, sm: StateManager):
        sm.set_region("g-1", "r-1", "R01", "测试区域")
        result = sm.get_region("g-1")
        assert result is not None
        assert result["region_id"] == "r-1"
        assert result["region_code"] == "R01"
        assert result["region_name"] == "测试区域"

    def test_get_region_missing_returns_none(self, sm: StateManager):
        assert sm.get_region("no-group") is None

    def test_remove_existing_region(self, sm: StateManager):
        sm.set_region("g-2", "r-2", "R02", "区域2")
        removed = sm.remove_region("g-2")
        assert removed is True
        assert sm.get_region("g-2") is None

    def test_remove_nonexistent_region_returns_false(self, sm: StateManager):
        assert sm.remove_region("ghost-group") is False

    def test_clear_all_regions(self, sm: StateManager):
        sm.set_region("g-a", "r-a", "RA", "A区")
        sm.set_region("g-b", "r-b", "RB", "B区")
        count = sm.clear_all_regions()
        assert count == 2
        assert sm.get_all_regions() == {}


# ---------------------------------------------------------------------------
# Location cache
# ---------------------------------------------------------------------------

class TestLocationCache:
    def test_set_and_get_location(self, sm: StateManager):
        sm.set_location("g-1", "loc-1", "诊室")
        result = sm.get_location("g-1")
        assert result is not None
        assert result["location_id"] == "loc-1"
        assert result["location_name"] == "诊室"

    def test_get_location_missing(self, sm: StateManager):
        assert sm.get_location("no-group") is None

    def test_remove_location(self, sm: StateManager):
        sm.set_location("g-2", "loc-2", "走廊")
        removed = sm.remove_location("g-2")
        assert removed is True
        assert sm.get_location("g-2") is None

    def test_remove_nonexistent_location(self, sm: StateManager):
        assert sm.remove_location("ghost-group") is False

    def test_clear_all_locations(self, sm: StateManager):
        sm.set_location("g-x", "lx", "X区")
        count = sm.clear_all_locations()
        assert count == 1
        assert sm.get_all_locations() == {}


# ---------------------------------------------------------------------------
# Session cache
# ---------------------------------------------------------------------------

class TestSessionCache:
    def test_set_and_get_session(self, sm: StateManager):
        sm.set_session("g-1", "sess-abc")
        result = sm.get_session("g-1")
        assert result == "sess-abc"

    def test_get_session_missing(self, sm: StateManager):
        assert sm.get_session("no-group") is None

    def test_clear_session(self, sm: StateManager):
        sm.set_session("g-1", "sess-abc")
        sm.clear_session("g-1")
        assert sm.get_session("g-1") is None

    def test_clear_session_also_clears_event_check(self, sm: StateManager):
        sm.set_session("g-1", "sess-1")
        sm.set_last_event_check("g-1", "u-1", "心灵感应")
        # 清除 session 时同步清除该 group 的 event check 缓存
        sm.clear_session("g-1")
        assert sm.get_last_event_check("g-1", "u-1") is None

    def test_clear_all_sessions(self, sm: StateManager):
        sm.set_session("g-a", "s1")
        sm.set_session("g-b", "s2")
        count = sm.clear_all_sessions()
        assert count == 2
        assert sm.get_all_sessions() == {}


# ---------------------------------------------------------------------------
# Last event check (in-memory)
# ---------------------------------------------------------------------------

class TestLastEventCheck:
    def test_set_and_get(self, sm: StateManager):
        sm.set_last_event_check("g-1", "u-1", "黑暗感知")
        result = sm.get_last_event_check("g-1", "u-1")
        assert result == "黑暗感知"

    def test_different_users_isolated(self, sm: StateManager):
        sm.set_last_event_check("g-1", "u-1", "检定A")
        sm.set_last_event_check("g-1", "u-2", "检定B")
        assert sm.get_last_event_check("g-1", "u-1") == "检定A"
        assert sm.get_last_event_check("g-1", "u-2") == "检定B"

    def test_different_groups_isolated(self, sm: StateManager):
        sm.set_last_event_check("g-1", "u-1", "检定X")
        sm.set_last_event_check("g-2", "u-1", "检定Y")
        assert sm.get_last_event_check("g-1", "u-1") == "检定X"
        assert sm.get_last_event_check("g-2", "u-1") == "检定Y"

    def test_missing_returns_none(self, sm: StateManager):
        assert sm.get_last_event_check("g-999", "u-999") is None


# ---------------------------------------------------------------------------
# clear_all
# ---------------------------------------------------------------------------

class TestClearAll:
    def test_returns_counts(self, sm: StateManager):
        sm.set_user("q1", "u1", "user1")
        sm.set_region("g1", "r1", "R1", "区域1")
        sm.set_location("g1", "l1", "地点1")
        sm.set_session("g1", "s1")

        result = sm.clear_all()
        assert result["user"] == 1
        assert result["region"] == 1
        assert result["location"] == 1
        assert result["session"] == 1

    def test_clear_all_when_empty(self, sm: StateManager):
        result = sm.clear_all()
        assert all(v == 0 for v in result.values())
