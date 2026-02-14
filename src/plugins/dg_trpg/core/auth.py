from __future__ import annotations

from .api_client import get_client
from .errors import DgCoreError, NeedRegistration
from .state import get_state


async def resolve_user(qq_uid: str) -> str:
    """Resolve QQ UID to dg-core user_id. Uses cache, falls back to API."""
    state = get_state()
    cached = state.get_user(qq_uid)
    if cached:
        return cached["user_id"]

    client = get_client()
    try:
        data = await client.resolve_platform("qq", qq_uid)
    except DgCoreError as e:
        if e.status_code == 404:
            raise NeedRegistration(qq_uid)
        raise

    user_id = data.get("user_id", "")
    username = data.get("username", "")
    if not user_id:
        raise NeedRegistration(qq_uid)

    state.set_user(qq_uid, user_id, username)
    return user_id
