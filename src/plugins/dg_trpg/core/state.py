from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import nonebot_plugin_localstore as store


class StateManager:
    """Manages local JSON state files via nonebot-plugin-localstore."""

    def __init__(self) -> None:
        data_dir: Path = store.get_data_dir("dg_trpg")
        data_dir.mkdir(parents=True, exist_ok=True)

        self._user_cache_path = data_dir / "user_cache.json"
        self._group_regions_path = data_dir / "group_regions.json"
        self._group_locations_path = data_dir / "group_locations.json"
        self._session_cache_path = data_dir / "session_cache.json"
        self._last_event_check: dict[str, str] = {}  # in-memory: "group:user" → event_name

    # --- File I/O helpers ---

    def _read(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return {}
        return json.loads(text)

    def _write(self, path: Path, data: dict[str, Any]) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- User cache ---

    def get_user(self, qq_uid: str) -> dict[str, str] | None:
        data = self._read(self._user_cache_path)
        return data.get(qq_uid)

    def set_user(self, qq_uid: str, user_id: str, username: str) -> None:
        data = self._read(self._user_cache_path)
        data[qq_uid] = {"user_id": user_id, "username": username}
        self._write(self._user_cache_path, data)

    def remove_user(self, qq_uid: str) -> bool:
        data = self._read(self._user_cache_path)
        if qq_uid in data:
            del data[qq_uid]
            self._write(self._user_cache_path, data)
            return True
        return False

    # --- Group regions ---

    def get_region(self, group_id: str) -> dict[str, str] | None:
        data = self._read(self._group_regions_path)
        return data.get(group_id)

    def set_region(
        self, group_id: str, region_id: str, region_code: str, region_name: str
    ) -> None:
        data = self._read(self._group_regions_path)
        data[group_id] = {
            "region_id": region_id,
            "region_code": region_code,
            "region_name": region_name,
        }
        self._write(self._group_regions_path, data)

    def remove_region(self, group_id: str) -> bool:
        data = self._read(self._group_regions_path)
        if group_id in data:
            del data[group_id]
            self._write(self._group_regions_path, data)
            return True
        return False

    # --- Group locations ---

    def get_location(self, group_id: str) -> dict[str, str] | None:
        data = self._read(self._group_locations_path)
        return data.get(group_id)

    def set_location(self, group_id: str, location_id: str, location_name: str) -> None:
        data = self._read(self._group_locations_path)
        data[group_id] = {"location_id": location_id, "location_name": location_name}
        self._write(self._group_locations_path, data)

    def remove_location(self, group_id: str) -> bool:
        data = self._read(self._group_locations_path)
        if group_id in data:
            del data[group_id]
            self._write(self._group_locations_path, data)
            return True
        return False

    # --- Session cache ---

    def get_session(self, group_id: str) -> str | None:
        data = self._read(self._session_cache_path)
        return data.get(group_id)

    def set_session(self, group_id: str, session_id: str) -> None:
        data = self._read(self._session_cache_path)
        data[group_id] = session_id
        self._write(self._session_cache_path, data)

    def clear_session(self, group_id: str) -> None:
        data = self._read(self._session_cache_path)
        if group_id in data:
            del data[group_id]
            self._write(self._session_cache_path, data)
        # Also clear any cached last-event-check for this group
        keys_to_remove = [k for k in self._last_event_check if k.startswith(f"{group_id}:")]
        for k in keys_to_remove:
            del self._last_event_check[k]

    # --- Last event check (in-memory, per user per group) ---

    def set_last_event_check(self, group_id: str, user_id: str, event_name: str) -> None:
        self._last_event_check[f"{group_id}:{user_id}"] = event_name

    def get_last_event_check(self, group_id: str, user_id: str) -> str | None:
        return self._last_event_check.get(f"{group_id}:{user_id}")

    # --- Bulk read ---

    def get_all_users(self) -> dict[str, Any]:
        return self._read(self._user_cache_path)

    def get_all_regions(self) -> dict[str, Any]:
        return self._read(self._group_regions_path)

    def get_all_locations(self) -> dict[str, Any]:
        return self._read(self._group_locations_path)

    def get_all_sessions(self) -> dict[str, Any]:
        return self._read(self._session_cache_path)

    # --- Bulk clear ---

    def clear_all_users(self) -> int:
        """Clear entire user cache. Returns number of entries removed."""
        data = self._read(self._user_cache_path)
        count = len(data)
        if count:
            self._write(self._user_cache_path, {})
        return count

    def clear_all_regions(self) -> int:
        """Clear all group-to-region bindings. Returns number of entries removed."""
        data = self._read(self._group_regions_path)
        count = len(data)
        if count:
            self._write(self._group_regions_path, {})
        return count

    def clear_all_locations(self) -> int:
        """Clear all group-to-location bindings. Returns number of entries removed."""
        data = self._read(self._group_locations_path)
        count = len(data)
        if count:
            self._write(self._group_locations_path, {})
        return count

    def clear_all_sessions(self) -> int:
        """Clear all session cache entries and in-memory event checks. Returns number removed."""
        data = self._read(self._session_cache_path)
        count = len(data)
        if count:
            self._write(self._session_cache_path, {})
        self._last_event_check.clear()
        return count

    def clear_all(self) -> dict[str, int]:
        """Clear all caches. Returns counts per cache type."""
        return {
            "user": self.clear_all_users(),
            "region": self.clear_all_regions(),
            "location": self.clear_all_locations(),
            "session": self.clear_all_sessions(),
        }


_state: StateManager | None = None


def get_state() -> StateManager:
    global _state
    if _state is None:
        _state = StateManager()
    return _state
