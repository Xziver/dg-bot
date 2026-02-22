from pathlib import Path

import nonebot
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="电子幽灵TRPG",
    description="Digital Ghost TRPG QQ Bot - 小倩",
    usage="/help 查看帮助",
)

sub_plugins = nonebot.load_plugins(str(Path(__file__).parent / "plugins"))

# Register startup cache validation hook
from .core import cache_validator  # noqa: F401
