from __future__ import annotations

from typing import Any

import httpx
import nonebot
from nonebot import get_plugin_config

from ..config import Config
from .errors import DgCoreError


class DgCoreClient:
    """Async HTTP client for dg-core REST API."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"X-API-Key": api_key},
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            resp = await self._http.request(method, path, json=json, params=params)
        except httpx.HTTPError:
            raise DgCoreError(0, "无法连接到游戏服务器，请稍后再试")
        if resp.status_code >= 400:
            detail = ""
            try:
                body = resp.json()
                detail = body.get("detail", str(body))
            except Exception:
                detail = resp.text
            raise DgCoreError(resp.status_code, detail)
        if resp.status_code == 204:
            return {}
        return resp.json()

    # ── Auth ───────────────────────────────────────────────

    async def register(
        self,
        username: str,
        password: str,
        platform: str = "qq",
        platform_uid: str = "",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"username": username, "password": password}
        if platform and platform_uid:
            payload["platform"] = platform
            payload["platform_uid"] = platform_uid
        return await self._request("POST", "/api/auth/register", json=payload)

    async def resolve_platform(self, platform: str, platform_uid: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/auth/resolve-platform",
            json={"platform": platform, "platform_uid": platform_uid},
        )

    # ── Characters ─────────────────────────────────────────

    async def get_active_character(self, game_id: str, user_id: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/api/games/{game_id}/characters/active",
            params={"user_id": user_id},
        )

    async def list_characters(self, game_id: str, user_id: str) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            f"/api/games/{game_id}/characters",
            params={"user_id": user_id},
        )
        if isinstance(data, list):
            return data
        return data.get("characters", data.get("items", []))

    async def switch_character(
        self, game_id: str, user_id: str, patient_id: str
    ) -> dict[str, Any]:
        return await self._request(
            "PUT",
            f"/api/games/{game_id}/characters/active",
            json={"patient_id": patient_id},
            params={"user_id": user_id},
        )

    async def set_attribute(
        self, game_id: str, user_id: str, ghost_id: str, attr: str, value: Any
    ) -> dict[str, Any]:
        """Set a ghost attribute via dispatcher (attribute_set event)."""
        return await self.submit_event(
            game_id, None, user_id,
            {"event_type": "attribute_set", "ghost_id": ghost_id, "attribute": attr, "value": value},
        )

    async def delete_character(
        self, game_id: str, patient_id: str, user_id: str
    ) -> dict[str, Any]:
        return await self._request(
            "DELETE",
            f"/api/games/{game_id}/characters/{patient_id}",
            params={"user_id": user_id},
        )

    async def create_patient(
        self,
        game_id: str,
        name: str,
        soul_color: str,
        user_id: str,
        *,
        gender: str = "",
        age: int | None = None,
        identity: str = "",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": name,
            "soul_color": soul_color,
            "user_id": user_id,
        }
        if gender:
            payload["gender"] = gender
        if age is not None:
            payload["age"] = age
        if identity:
            payload["identity"] = identity
        return await self._request(
            "POST", f"/api/games/{game_id}/characters/patients", json=payload
        )

    async def create_ghost(
        self,
        game_id: str,
        name: str,
        soul_color: str,
        *,
        origin_patient_id: str,
        creator_user_id: str,
        initial_hp: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": name,
            "soul_color": soul_color,
            "origin_patient_id": origin_patient_id,
            "creator_user_id": creator_user_id,
        }
        if initial_hp is not None:
            payload["initial_hp"] = initial_hp
        return await self._request(
            "POST", f"/api/games/{game_id}/characters/ghosts", json=payload
        )

    async def assign_companion(
        self, game_id: str, ghost_id: str, patient_id: str, user_id: str
    ) -> dict[str, Any]:
        return await self._request(
            "PUT",
            f"/api/games/{game_id}/ghosts/{ghost_id}/companion",
            json={"patient_id": patient_id},
        )

    async def get_abilities(
        self, ghost_id: str, *, game_id: str = ""
    ) -> list[dict[str, Any]]:
        if not game_id:
            raise DgCoreError(0, "game_id is required for get_abilities")
        data = await self._request(
            "GET", f"/api/games/{game_id}/ghosts/{ghost_id}/abilities"
        )
        if isinstance(data, list):
            return data
        return data.get("abilities", [])

    # ── Events (Dispatcher) ───────────────────────────────

    async def submit_event(
        self,
        game_id: str,
        session_id: str | None,
        user_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "game_id": game_id,
            "user_id": user_id,
            "payload": payload,
        }
        if session_id:
            body["session_id"] = session_id
        return await self._request("POST", "/api/events", json=body)

    # ── Event Definitions ─────────────────────────────────

    async def define_event(
        self,
        session_id: str,
        game_id: str,
        name: str,
        expression: str,
        *,
        color_restriction: str | None = None,
        user_id: str = "",
    ) -> dict[str, Any]:
        """Define a new event check via dispatcher (event_define event)."""
        event_payload: dict[str, Any] = {
            "event_type": "event_define",
            "name": name,
            "expression": expression,
        }
        if color_restriction:
            event_payload["color_restriction"] = color_restriction.upper()
        return await self.submit_event(game_id, session_id, user_id, event_payload)

    async def list_events(self, session_id: str) -> list[dict[str, Any]]:
        data = await self._request(
            "GET", f"/api/sessions/{session_id}/event-definitions"
        )
        if isinstance(data, list):
            return data
        return data.get("events", [])

    async def delete_event(
        self, session_id: str, event_id: str, *, game_id: str = "", user_id: str = ""
    ) -> dict[str, Any]:
        """Deactivate an event definition via dispatcher (event_deactivate event)."""
        return await self.submit_event(
            game_id, session_id, user_id,
            {"event_type": "event_deactivate", "event_def_id": event_id},
        )

    # ── Session Management ─────────────────────────────────

    async def pause_session(self, session_id: str, *, user_id: str = "") -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/sessions/{session_id}/pause",
            params={"user_id": user_id} if user_id else None,
        )

    async def resume_session(self, session_id: str, *, user_id: str = "") -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/sessions/{session_id}/resume",
            params={"user_id": user_id} if user_id else None,
        )

    async def get_session_info(self, session_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/sessions/{session_id}")

    async def add_session_player(
        self, session_id: str, patient_id: str, *, user_id: str = ""
    ) -> dict[str, Any]:
        return await self._request(
            "POST", f"/api/sessions/{session_id}/players",
            json={"patient_id": patient_id},
            params={"user_id": user_id} if user_id else None,
        )

    async def remove_session_player(
        self, session_id: str, patient_id: str, *, user_id: str = ""
    ) -> dict[str, Any]:
        return await self._request(
            "DELETE",
            f"/api/sessions/{session_id}/players/{patient_id}",
            params={"user_id": user_id} if user_id else None,
        )

    # ── Buffs ──────────────────────────────────────────────

    async def add_buff(
        self,
        game_id: str,
        ghost_id: str,
        name: str,
        expression: str,
        *,
        rounds: int = 1,
        user_id: str = "",
    ) -> dict[str, Any]:
        """Add a buff via dispatcher (buff_add event)."""
        return await self.submit_event(
            game_id, None, user_id,
            {
                "event_type": "buff_add",
                "ghost_id": ghost_id,
                "name": name,
                "expression": expression,
                "remaining_rounds": rounds,
            },
        )

    async def list_buffs(self, game_id: str, ghost_id: str) -> list[dict[str, Any]]:
        data = await self._request(
            "GET", f"/api/games/{game_id}/ghosts/{ghost_id}/buffs"
        )
        if isinstance(data, list):
            return data
        return data.get("buffs", [])

    async def remove_buff(
        self, game_id: str, buff_id: str, *, user_id: str = ""
    ) -> dict[str, Any]:
        """Remove a buff via dispatcher (buff_remove event)."""
        return await self.submit_event(
            game_id, None, user_id,
            {"event_type": "buff_remove", "buff_id": buff_id},
        )

    # ── Items ──────────────────────────────────────────────

    async def create_item_definition(
        self,
        game_id: str,
        name: str,
        *,
        description: str = "",
        effects: list[dict[str, Any]] | None = None,
        user_id: str = "",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name}
        if description:
            payload["description"] = description
        if effects:
            payload["effects"] = effects
        return await self._request(
            "POST", f"/api/games/{game_id}/items/definitions", json=payload,
            params={"user_id": user_id} if user_id else None,
        )

    async def list_item_definitions(self, game_id: str) -> list[dict[str, Any]]:
        data = await self._request(
            "GET", f"/api/games/{game_id}/items/definitions"
        )
        if isinstance(data, list):
            return data
        return data.get("items", [])

    async def grant_item(
        self,
        game_id: str,
        user_id: str,
        patient_id: str,
        item_def_id: str,
        *,
        count: int = 1,
    ) -> dict[str, Any]:
        """Grant an item via dispatcher (item_grant event)."""
        return await self.submit_event(
            game_id, None, user_id,
            {
                "event_type": "item_grant",
                "patient_id": patient_id,
                "item_def_id": item_def_id,
                "count": count,
            },
        )

    async def get_inventory(self, game_id: str, user_id: str) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            f"/api/games/{game_id}/items/inventory",
            params={"user_id": user_id},
        )
        if isinstance(data, list):
            return data
        return data.get("items", [])

    # ── Dice ───────────────────────────────────────────────

    async def roll_dice(
        self,
        expression: str,
        *,
        game_id: str = "",
        user_id: str = "",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"expression": expression}
        if game_id:
            payload["game_id"] = game_id
        if user_id:
            payload["user_id"] = user_id
        return await self._request("POST", "/api/dice/roll", json=payload)

    # ── Regions / Locations ────────────────────────────────

    async def create_region(
        self, game_id: str, code: str, name: str, *, user_id: str = ""
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": code, "name": name}
        return await self._request(
            "POST", f"/api/games/{game_id}/regions", json=payload,
            params={"user_id": user_id} if user_id else None,
        )

    async def list_regions(self, game_id: str) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/api/games/{game_id}/regions")
        if isinstance(data, list):
            return data
        return data.get("regions", [])

    async def create_location(
        self,
        game_id: str,
        region_id: str,
        name: str,
        *,
        description: str = "",
        user_id: str = "",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name}
        if description:
            payload["description"] = description
        return await self._request(
            "POST",
            f"/api/games/{game_id}/regions/{region_id}/locations",
            json=payload,
            params={"user_id": user_id} if user_id else None,
        )

    async def list_locations(
        self, game_id: str, region_id: str
    ) -> list[dict[str, Any]]:
        data = await self._request(
            "GET", f"/api/games/{game_id}/regions/{region_id}/locations"
        )
        if isinstance(data, list):
            return data
        return data.get("locations", [])

    async def get_location_players(
        self, game_id: str, location_id: str
    ) -> list[dict[str, Any]]:
        data = await self._request(
            "GET", f"/api/games/{game_id}/locations/{location_id}/players"
        )
        if isinstance(data, list):
            return data
        return data.get("players", [])

    # ── Communication ──────────────────────────────────────

    async def list_pending_comms(
        self, game_id: str, user_id: str
    ) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            f"/api/games/{game_id}/communications/pending",
            params={"user_id": user_id},
        )
        if isinstance(data, list):
            return data
        return data.get("communications", [])

    # ── Timeline ───────────────────────────────────────────

    async def get_session_timeline(
        self, session_id: str, *, limit: int | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        data = await self._request(
            "GET", f"/api/sessions/{session_id}/timeline", params=params or None
        )
        if isinstance(data, list):
            return data
        return data.get("entries", data.get("events", []))

    async def get_game_timeline(
        self, game_id: str, *, limit: int | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        data = await self._request(
            "GET", f"/api/games/{game_id}/timeline", params=params or None
        )
        if isinstance(data, list):
            return data
        return data.get("entries", data.get("events", []))

    # ── Game ───────────────────────────────────────────────

    async def get_game_info(self, game_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/games/{game_id}")

    async def add_game_player(
        self, game_id: str, user_id: str, *, role: str = "PL"
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/games/{game_id}/players",
            json={"user_id": user_id, "role": role},
        )

    async def update_game_player_role(
        self, game_id: str, user_id: str, role: str
    ) -> dict[str, Any]:
        return await self._request(
            "PUT",
            f"/api/games/{game_id}/players/{user_id}/role",
            json={"role": role},
        )


# ── Singleton ──────────────────────────────────────────────

_client: DgCoreClient | None = None


def get_client() -> DgCoreClient:
    global _client
    if _client is None:
        config = get_plugin_config(Config)
        _client = DgCoreClient(config.dg_core_url, config.dg_bot_api_key)
    return _client


def _register_shutdown() -> None:
    try:
        driver = nonebot.get_driver()

        @driver.on_shutdown
        async def _shutdown() -> None:
            global _client
            if _client is not None:
                await _client.close()
                _client = None

    except Exception:
        pass


_register_shutdown()
