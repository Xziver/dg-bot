from __future__ import annotations

from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageEvent
from nonebot.params import CommandArg
from nonebot import get_plugin_config

from ..config import Config
from .auth import resolve_user
from .errors import GameNotConfigured, LocationNotBound, NeedRegistration, NoActiveSession, RegionNotBound
from .state import get_state

# Characters in TRPG never have purely numeric names, so this threshold
# distinguishes QQ numbers from character names reliably.
_QQ_UID_MIN_DIGITS = 5


def get_group_id(event: GroupMessageEvent) -> str:
    return str(event.group_id)


def get_qq_uid(event: MessageEvent) -> str:
    return str(event.user_id)


async def get_dg_user_id(event: GroupMessageEvent) -> str:
    qq_uid = get_qq_uid(event)
    return await resolve_user(qq_uid)


def get_game_id() -> str:
    config = get_plugin_config(Config)
    if not config.dg_game_id:
        raise GameNotConfigured()
    return config.dg_game_id


def get_region_id(event: GroupMessageEvent) -> str:
    group_id = get_group_id(event)
    region = get_state().get_region(group_id)
    if not region:
        raise RegionNotBound(group_id)
    return region["region_id"]


def get_location_id(event: GroupMessageEvent) -> str:
    group_id = get_group_id(event)
    location = get_state().get_location(group_id)
    if not location:
        raise LocationNotBound(group_id)
    return location["location_id"]


def get_session_id(event: GroupMessageEvent) -> str:
    group_id = get_group_id(event)
    session_id = get_state().get_session(group_id)
    if not session_id:
        raise NoActiveSession(group_id)
    return session_id


def get_mentioned_qq_uid(args: Message) -> str | None:
    """Extract the first @mention QQ UID from command args."""
    for seg in args:
        if seg.type == "at":
            qq = seg.data.get("qq", "")
            if qq:
                return str(qq)
    return None


def get_plain_args(args: Message) -> str:
    """Extract plain text from command args, excluding @mentions."""
    parts: list[str] = []
    for seg in args:
        if seg.type == "text":
            parts.append(str(seg.data.get("text", "")))
    return " ".join(parts).strip()


async def resolve_player_target(args: Message, sub_args: str) -> str | None:
    """Resolve a player target from @mention, QQ number, or character name.

    Resolution order:
      1. @mention in message → resolve QQ UID to dg-core user_id
      2. Pure numeric string (≥5 digits) in *sub_args* → treat as QQ号, resolve
      3. Non-numeric string in *sub_args* → return as-is (character name / ID)

    Returns ``None`` when *sub_args* is empty **and** no @mention is present.
    """
    # 1. @mention
    mentioned = get_mentioned_qq_uid(args)
    if mentioned:
        try:
            return await resolve_user(mentioned)
        except NeedRegistration as e:
            raise NeedRegistration(e.qq_uid, is_target=True) from e

    target = sub_args.strip()
    if not target:
        return None

    # 2. Bare QQ number
    if target.isdigit() and len(target) >= _QQ_UID_MIN_DIGITS:
        try:
            return await resolve_user(target)
        except NeedRegistration as e:
            raise NeedRegistration(e.qq_uid, is_target=True) from e

    # 3. Character name / other identifier — pass through for API resolution
    return target


async def resolve_patient_id(game_id: str, user_id: str, target: str) -> str:
    """Resolve a character name or ID to its patient_id.

    Tries matching by patient_id/id first, then by name.
    Returns *target* unchanged if no match is found.
    """
    from .api_client import get_client

    client = get_client()
    characters = await client.list_characters(game_id, user_id)
    for ch in characters:
        pid = ch.get("patient_id", ch.get("id", ""))
        if pid and pid == target:
            return pid
    for ch in characters:
        if ch.get("name") == target:
            return ch.get("patient_id", ch.get("id", target))
    return target
