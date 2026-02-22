"""Startup cache validation for dg-trpg.

Validates all cached entries against the dg-core backend on bot startup.
Stale entries are cleared. If backend is unreachable, validation is skipped.
"""

from __future__ import annotations

import logging
import random

import nonebot
from nonebot import get_plugin_config

from ..config import Config
from .api_client import get_client
from .errors import DgCoreError
from .state import get_state

logger = logging.getLogger("dg_trpg.cache_validator")

_USER_SAMPLE_SIZE = 3


async def _validate_users() -> tuple[int, int]:
    """Validate user cache by sampling. Returns (kept, cleared) counts."""
    state = get_state()
    client = get_client()
    users = state.get_all_users()

    if not users:
        return 0, 0

    sample_keys = random.sample(list(users.keys()), min(_USER_SAMPLE_SIZE, len(users)))
    stale_found = False

    for qq_uid in sample_keys:
        try:
            await client.resolve_platform("qq", qq_uid)
        except DgCoreError as e:
            if e.status_code == 404:
                stale_found = True
                logger.info("Sampled user QQ:%s returned 404, backend likely reset", qq_uid)
                break
            else:
                logger.warning("Failed to validate user QQ:%s: %s", qq_uid, e)

    if stale_found:
        count = state.clear_all_users()
        logger.warning("Backend reset detected. Cleared entire user cache (%d entries)", count)
        return 0, count

    return len(users), 0


async def _validate_regions(game_id: str) -> tuple[int, int]:
    """Validate region bindings against backend. Returns (kept, cleared) counts."""
    state = get_state()
    client = get_client()
    regions_cache = state.get_all_regions()

    if not regions_cache:
        return 0, 0

    try:
        backend_regions = await client.list_regions(game_id)
    except DgCoreError:
        logger.warning("Failed to fetch regions for validation, skipping")
        return len(regions_cache), 0

    valid_region_ids = {r.get("id") for r in backend_regions}
    kept, cleared = 0, 0

    for group_id, region_data in list(regions_cache.items()):
        if region_data.get("region_id") in valid_region_ids:
            kept += 1
        else:
            state.remove_region(group_id)
            cleared += 1
            logger.info(
                "Cleared stale region binding for group %s (region %s no longer exists)",
                group_id,
                region_data.get("region_id"),
            )

    return kept, cleared


async def _validate_locations(game_id: str) -> tuple[int, int]:
    """Validate location bindings against backend. Returns (kept, cleared) counts."""
    state = get_state()
    client = get_client()
    locations_cache = state.get_all_locations()
    regions_cache = state.get_all_regions()

    if not locations_cache:
        return 0, 0

    # Build valid location_ids by fetching locations for each bound region
    valid_location_ids: set[str] = set()
    seen_region_ids: set[str] = set()

    for region_data in regions_cache.values():
        rid = region_data.get("region_id", "")
        if rid and rid not in seen_region_ids:
            seen_region_ids.add(rid)
            try:
                locs = await client.list_locations(game_id, rid)
                for loc in locs:
                    loc_id = loc.get("id", "")
                    if loc_id:
                        valid_location_ids.add(loc_id)
            except DgCoreError:
                logger.warning("Failed to fetch locations for region %s, skipping", rid)

    # Groups with no region binding also have stale location bindings
    groups_with_region = set(regions_cache.keys())

    kept, cleared = 0, 0
    for group_id, loc_data in list(locations_cache.items()):
        loc_id = loc_data.get("location_id", "")
        if group_id not in groups_with_region:
            state.remove_location(group_id)
            cleared += 1
            logger.info("Cleared location for group %s (region also cleared)", group_id)
        elif loc_id in valid_location_ids:
            kept += 1
        else:
            state.remove_location(group_id)
            cleared += 1
            logger.info(
                "Cleared stale location for group %s (location %s no longer exists)",
                group_id,
                loc_id,
            )

    return kept, cleared


async def _validate_sessions() -> tuple[int, int]:
    """Validate session cache. Returns (kept, cleared) counts."""
    state = get_state()
    client = get_client()
    sessions = state.get_all_sessions()
    kept, cleared = 0, 0

    for group_id, session_id in list(sessions.items()):
        try:
            info = await client.get_session_info(session_id)
            status = info.get("status", info.get("data", {}).get("status", ""))
            if status in ("active", "paused"):
                kept += 1
            else:
                state.clear_session(group_id)
                cleared += 1
                logger.info("Cleared ended session %s for group %s", session_id, group_id)
        except DgCoreError as e:
            if e.status_code == 404:
                state.clear_session(group_id)
                cleared += 1
                logger.info("Cleared stale session %s for group %s (404)", session_id, group_id)
            else:
                logger.warning("Failed to validate session %s: %s", session_id, e)
                kept += 1  # Keep on non-404 errors (might be transient)

    return kept, cleared


async def validate_caches() -> None:
    """Run full cache validation. Called on bot startup and by /cache validate."""
    config = get_plugin_config(Config)
    game_id = config.dg_game_id

    if not game_id:
        logger.warning("DG_GAME_ID not configured, skipping cache validation")
        return

    logger.info("Starting cache validation...")

    try:
        u_kept, u_cleared = await _validate_users()
        logger.info("Users: kept=%d, cleared=%d", u_kept, u_cleared)

        r_kept, r_cleared = await _validate_regions(game_id)
        logger.info("Regions: kept=%d, cleared=%d", r_kept, r_cleared)

        # Location validation depends on regions being validated first
        l_kept, l_cleared = await _validate_locations(game_id)
        logger.info("Locations: kept=%d, cleared=%d", l_kept, l_cleared)

        s_kept, s_cleared = await _validate_sessions()
        logger.info("Sessions: kept=%d, cleared=%d", s_kept, s_cleared)

        total_cleared = u_cleared + r_cleared + l_cleared + s_cleared
        if total_cleared:
            logger.warning("Cache validation complete: %d stale entries cleared", total_cleared)
        else:
            logger.info("Cache validation complete: all entries valid")

    except Exception:
        logger.exception("Cache validation failed unexpectedly, continuing with existing cache")


def _register_startup() -> None:
    try:
        driver = nonebot.get_driver()

        @driver.on_startup
        async def _startup_validate() -> None:
            await validate_caches()

    except Exception:
        pass


_register_startup()
