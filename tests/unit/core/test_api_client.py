"""单元测试 — src/plugins/dg_trpg/core/api_client.py

覆盖范围:
- DgCoreClient 各 HTTP 方法（成功路径 & 错误路径）
- 认证头正确携带
- 4xx/5xx 响应抛出 DgCoreError
- 连接失败抛出 DgCoreError(0)
- 204 No Content 返回空字典

依赖隔离: 使用 respx 拦截 httpx 请求，完全无真实网络调用。
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

import httpx
import pytest
import respx

from src.plugins.dg_trpg.core.api_client import DgCoreClient
from src.plugins.dg_trpg.core.errors import DgCoreError

BASE_URL = "http://test.local"
API_KEY = "test-api-key"


@pytest.fixture
async def client() -> AsyncGenerator[DgCoreClient, None]:
    """返回指向 test.local 的 DgCoreClient，测试结束后关闭。"""
    c = DgCoreClient(BASE_URL, API_KEY)
    yield c
    await c.close()


# ---------------------------------------------------------------------------
# 辅助：构造标准 JSON 响应
# ---------------------------------------------------------------------------

def json_resp(data: dict | list, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=data)


def error_resp(status: int, detail: str = "error") -> httpx.Response:
    return httpx.Response(status, json={"detail": detail})


# ---------------------------------------------------------------------------
# 认证头
# ---------------------------------------------------------------------------

class TestAuthHeader:
    @respx.mock
    async def test_api_key_header_sent(self, client: DgCoreClient):
        mock_route = respx.post(f"{BASE_URL}/api/dice/roll").mock(
            return_value=json_resp({"total": 5})
        )
        await client.roll_dice("d6")
        assert mock_route.called
        request = mock_route.calls.last.request
        assert request.headers.get("x-api-key") == API_KEY


# ---------------------------------------------------------------------------
# Dice
# ---------------------------------------------------------------------------

class TestRollDice:
    @respx.mock
    async def test_basic_roll(self, client: DgCoreClient):
        respx.post(f"{BASE_URL}/api/dice/roll").mock(
            return_value=json_resp({"expression": "2d6", "results": [3, 4], "total": 7})
        )
        result = await client.roll_dice("2d6")
        assert result["total"] == 7

    @respx.mock
    async def test_roll_with_game_and_user(self, client: DgCoreClient):
        route = respx.post(f"{BASE_URL}/api/dice/roll").mock(
            return_value=json_resp({"total": 5})
        )
        await client.roll_dice("d6", game_id="g-1", user_id="u-1")
        request = route.calls.last.request
        import json
        body = json.loads(request.content)
        assert body["game_id"] == "g-1"
        assert body["user_id"] == "u-1"

    @respx.mock
    async def test_400_raises_dg_core_error(self, client: DgCoreClient):
        respx.post(f"{BASE_URL}/api/dice/roll").mock(
            return_value=error_resp(400, "invalid expression")
        )
        with pytest.raises(DgCoreError) as exc_info:
            await client.roll_dice("???")
        assert exc_info.value.status_code == 400
        assert "invalid expression" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuth:
    @respx.mock
    async def test_register_success(self, client: DgCoreClient):
        respx.post(f"{BASE_URL}/api/auth/register").mock(
            return_value=json_resp({"user_id": "u-1", "api_key": "key-abc"})
        )
        data = await client.register("alice", "pass123", platform="qq", platform_uid="12345")
        assert data["user_id"] == "u-1"

    @respx.mock
    async def test_register_409_conflict(self, client: DgCoreClient):
        respx.post(f"{BASE_URL}/api/auth/register").mock(
            return_value=error_resp(409, "username taken")
        )
        with pytest.raises(DgCoreError) as exc_info:
            await client.register("alice", "pass")
        assert exc_info.value.status_code == 409

    @respx.mock
    async def test_resolve_platform(self, client: DgCoreClient):
        respx.post(f"{BASE_URL}/api/auth/resolve-platform").mock(
            return_value=json_resp({"user_id": "u-1", "username": "alice"})
        )
        data = await client.resolve_platform("qq", "12345")
        assert data["username"] == "alice"

    @respx.mock
    async def test_resolve_platform_404(self, client: DgCoreClient):
        respx.post(f"{BASE_URL}/api/auth/resolve-platform").mock(
            return_value=error_resp(404, "not found")
        )
        with pytest.raises(DgCoreError) as exc_info:
            await client.resolve_platform("qq", "99999")
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Characters
# ---------------------------------------------------------------------------

class TestCharacters:
    @respx.mock
    async def test_get_active_character(self, client: DgCoreClient):
        respx.get(f"{BASE_URL}/api/games/g-1/characters/active").mock(
            return_value=json_resp({"patient": {"id": "p1"}, "ghost": None})
        )
        data = await client.get_active_character("g-1", "u-1")
        assert data["patient"]["id"] == "p1"

    @respx.mock
    async def test_list_characters_list_response(self, client: DgCoreClient):
        respx.get(f"{BASE_URL}/api/games/g-1/characters").mock(
            return_value=json_resp([{"id": "c1"}, {"id": "c2"}])
        )
        result = await client.list_characters("g-1", "u-1")
        assert len(result) == 2

    @respx.mock
    async def test_list_characters_wrapped_response(self, client: DgCoreClient):
        """兼容 {characters: [...]} 包装格式。"""
        respx.get(f"{BASE_URL}/api/games/g-1/characters").mock(
            return_value=json_resp({"characters": [{"id": "c1"}]})
        )
        result = await client.list_characters("g-1", "u-1")
        assert len(result) == 1

    @respx.mock
    async def test_delete_character(self, client: DgCoreClient):
        respx.delete(f"{BASE_URL}/api/games/g-1/characters/p-1").mock(
            return_value=httpx.Response(204)
        )
        result = await client.delete_character("g-1", "p-1", "u-1")
        assert result == {}


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class TestSubmitEvent:
    @respx.mock
    async def test_submit_event_with_session(self, client: DgCoreClient):
        route = respx.post(f"{BASE_URL}/api/events").mock(
            return_value=json_resp({"success": True})
        )
        await client.submit_event("g-1", "s-1", "u-1", {"event_type": "event_check"})
        import json
        body = json.loads(route.calls.last.request.content)
        assert body["session_id"] == "s-1"
        assert body["game_id"] == "g-1"

    @respx.mock
    async def test_submit_event_without_session(self, client: DgCoreClient):
        route = respx.post(f"{BASE_URL}/api/events").mock(
            return_value=json_resp({"success": True})
        )
        await client.submit_event("g-1", None, "u-1", {"event_type": "buff_add"})
        import json
        body = json.loads(route.calls.last.request.content)
        assert "session_id" not in body


# ---------------------------------------------------------------------------
# Regions & Locations
# ---------------------------------------------------------------------------

class TestRegionsLocations:
    @respx.mock
    async def test_list_regions(self, client: DgCoreClient):
        respx.get(f"{BASE_URL}/api/games/g-1/regions").mock(
            return_value=json_resp([{"id": "r-1", "code": "R01", "name": "测试区域"}])
        )
        regions = await client.list_regions("g-1")
        assert regions[0]["code"] == "R01"

    @respx.mock
    async def test_create_region(self, client: DgCoreClient):
        route = respx.post(f"{BASE_URL}/api/games/g-1/regions").mock(
            return_value=json_resp({"id": "r-2", "code": "R02"})
        )
        result = await client.create_region("g-1", "R02", "新区域", user_id="u-1")
        assert result["id"] == "r-2"

    @respx.mock
    async def test_list_locations(self, client: DgCoreClient):
        respx.get(f"{BASE_URL}/api/games/g-1/regions/r-1/locations").mock(
            return_value=json_resp([{"id": "l-1", "name": "诊室"}])
        )
        locs = await client.list_locations("g-1", "r-1")
        assert locs[0]["name"] == "诊室"


# ---------------------------------------------------------------------------
# Buffs
# ---------------------------------------------------------------------------

class TestBuffs:
    @respx.mock
    async def test_list_buffs(self, client: DgCoreClient):
        respx.get(f"{BASE_URL}/api/games/g-1/ghosts/gh-1/buffs").mock(
            return_value=json_resp([{"id": "b-1", "name": "护盾"}])
        )
        buffs = await client.list_buffs("g-1", "gh-1")
        assert buffs[0]["name"] == "护盾"

    @respx.mock
    async def test_add_buff_via_event(self, client: DgCoreClient):
        """add_buff 通过 submit_event (buff_add) 实现。"""
        route = respx.post(f"{BASE_URL}/api/events").mock(
            return_value=json_resp({"success": True})
        )
        await client.add_buff("g-1", "gh-1", "护盾", "+2", rounds=3, user_id="u-1")
        import json
        body = json.loads(route.calls.last.request.content)
        assert body["payload"]["event_type"] == "buff_add"
        assert body["payload"]["remaining_rounds"] == 3


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class TestSession:
    @respx.mock
    async def test_get_session_info(self, client: DgCoreClient):
        respx.get(f"{BASE_URL}/api/sessions/s-1").mock(
            return_value=json_resp({"session_id": "s-1", "status": "active"})
        )
        data = await client.get_session_info("s-1")
        assert data["session_id"] == "s-1"

    @respx.mock
    async def test_pause_session(self, client: DgCoreClient):
        respx.post(f"{BASE_URL}/api/sessions/s-1/pause").mock(
            return_value=json_resp({"status": "paused"})
        )
        result = await client.pause_session("s-1")
        assert result["status"] == "paused"


# ---------------------------------------------------------------------------
# 连接错误
# ---------------------------------------------------------------------------

class TestConnectionError:
    @respx.mock
    async def test_connection_failure_raises_dg_core_error_0(
        self, client: DgCoreClient
    ):
        respx.post(f"{BASE_URL}/api/dice/roll").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        with pytest.raises(DgCoreError) as exc_info:
            await client.roll_dice("d6")
        assert exc_info.value.status_code == 0
        assert "无法连接" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 服务器错误
# ---------------------------------------------------------------------------

class TestServerErrors:
    @respx.mock
    async def test_500_raises_dg_core_error(self, client: DgCoreClient):
        respx.get(f"{BASE_URL}/api/games/g-1/regions").mock(
            return_value=error_resp(500, "internal error")
        )
        with pytest.raises(DgCoreError) as exc_info:
            await client.list_regions("g-1")
        assert exc_info.value.status_code == 500

    @respx.mock
    async def test_204_returns_empty_dict(self, client: DgCoreClient):
        respx.delete(f"{BASE_URL}/api/games/g-1/characters/p-1").mock(
            return_value=httpx.Response(204)
        )
        result = await client.delete_character("g-1", "p-1", "u-1")
        assert result == {}
