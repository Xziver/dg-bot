from __future__ import annotations

from nonebot import logger

from .api_client import get_client
from .errors import DgCoreError, NeedRegistration
from .state import get_state


async def resolve_user(qq_uid: str) -> str:
    """Resolve QQ UID to dg-core user_id. Uses cache, falls back to API."""
    state = get_state()
    cached = state.get_user(qq_uid)
    if cached:
        logger.debug("User resolved from cache: qq_uid={} -> user_id={}", qq_uid, cached["user_id"])
        return cached["user_id"]

    client = get_client()
    try:
        logger.info("Resolving user via API: qq_uid={}", qq_uid)
        data = await client.resolve_platform("qq", qq_uid)
    except DgCoreError as e:
        if e.status_code == 404:
            logger.warning("User not registered: qq_uid={}", qq_uid)
            raise NeedRegistration(qq_uid)
        raise

    user_id = data.get("user_id", "")
    username = data.get("username", "")
    if not user_id:
        logger.warning("User resolution returned empty user_id: qq_uid={}", qq_uid)
        raise NeedRegistration(qq_uid)

    state.set_user(qq_uid, user_id, username)
    logger.info("User resolved and cached: qq_uid={} -> user_id={}", qq_uid, user_id)
    return user_id
