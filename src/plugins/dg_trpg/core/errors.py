from __future__ import annotations


class DgCoreError(Exception):
    """dg-core API returned an error HTTP status."""

    def __init__(self, status_code: int, detail: str = "") -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class NeedRegistration(Exception):
    """Player has no dg-core account."""

    def __init__(self, qq_uid: str, *, is_target: bool = False) -> None:
        self.qq_uid = qq_uid
        self.is_target = is_target
        super().__init__(f"QQ user {qq_uid} not registered")


class RegionNotBound(Exception):
    """QQ group has no region binding."""

    def __init__(self, group_id: str) -> None:
        self.group_id = group_id
        super().__init__(f"Group {group_id} has no region binding")


class LocationNotBound(Exception):
    """QQ group has no location binding."""

    def __init__(self, group_id: str) -> None:
        self.group_id = group_id
        super().__init__(f"Group {group_id} has no location binding")


class NoActiveSession(Exception):
    """QQ group has no active session."""

    def __init__(self, group_id: str) -> None:
        self.group_id = group_id
        super().__init__(f"Group {group_id} has no active session")


class GameNotConfigured(Exception):
    """DG_GAME_ID env var is not set."""

    def __init__(self) -> None:
        super().__init__("DG_GAME_ID not configured")


class StaleCacheError(Exception):
    """A cached ID was rejected by the backend (404). Cache has been auto-cleared."""

    def __init__(self, cache_type: str, detail: str = "") -> None:
        self.cache_type = cache_type
        self.detail = detail
        super().__init__(f"Stale {cache_type} cache: {detail}")


class InsufficientPermission(Exception):
    """User lacks required permission."""

    def __init__(self, detail: str = "权限不足") -> None:
        self.detail = detail
        super().__init__(detail)


# --- Error formatting ---

_STATUS_MESSAGES: dict[int, str] = {
    400: "操作失败",
    401: "Bot认证失败，请联系管理员检查Bot配置",
    403: "权限不足",
    404: "未找到",
    422: "参数错误",
    500: "服务器错误，请稍后再试",
}


def format_api_error(e: DgCoreError) -> str:
    base = _STATUS_MESSAGES.get(e.status_code, f"请求错误 (HTTP {e.status_code})")
    if e.detail and e.status_code not in (401, 500):
        return f"{base}: {e.detail}"
    return base


def format_context_error(e: Exception) -> str | None:
    if isinstance(e, NeedRegistration):
        if e.is_target:
            return f"目标玩家 (QQ: {e.qq_uid}) 尚未注册"
        return "你尚未注册，请先使用 /register <用户名> <密码>"
    if isinstance(e, RegionNotBound):
        return "本群尚未绑定区域，请DM使用 /region bind <区域代码>"
    if isinstance(e, LocationNotBound):
        return "本群尚未绑定地点，请DM使用 /location bind <地点名称>"
    if isinstance(e, NoActiveSession):
        return "本群当前没有进行中的场次，请DM使用 /session start"
    if isinstance(e, GameNotConfigured):
        return "游戏尚未配置，请管理员设置 DG_GAME_ID"
    if isinstance(e, InsufficientPermission):
        return f"权限不足: {e.detail}"
    if isinstance(e, StaleCacheError):
        _stale_messages = {
            "user": "你的账号缓存已失效，请重新使用任意命令（将自动重新解析）。",
            "region": "本群绑定的区域已失效（后端数据已重置）。请DM使用 /region bind 重新绑定。",
            "location": "本群绑定的地点已失效（后端数据已重置）。请DM使用 /location bind 重新绑定。",
            "session": "缓存的场次已失效，已自动清除。请DM使用 /session start 创建新场次。",
        }
        return _stale_messages.get(e.cache_type, f"缓存已失效: {e.detail}")
    return None
