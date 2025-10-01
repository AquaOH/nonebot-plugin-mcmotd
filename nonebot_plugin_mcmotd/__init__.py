from nonebot.plugin import PluginMetadata

from .config import Config

__version__ = "1.0.1"

__plugin_meta__ = PluginMetadata(
    name="Minecraft MOTD 查询",
    description="查询多个 Minecraft 服务器状态并生成在一张图片上展示",
    usage=(
        "用户命令:\n"
        "/motd - 查询所有服务器状态\n"
        "/motd --detail - 显示详细信息包括玩家列表\n\n"
        "管理员命令:\n"
        "/motd add ip:port 标签 - 添加服务器\n"
        "/motd del ip:port - 删除服务器\n"
        "/motd del -rf - 删除所有服务器\n"
        "/motd help - 显示帮助信息\n\n"
        "管理员权限包括:\n"
        "- NoneBot 超级管理员 (SUPERUSERS)\n"
        "- 插件超级管理员 (MC_MOTD_SUPERUSERS)\n"
        "- 群管理员或群主 (需开启群管理员权限)"
    ),
    type="application",
    homepage="https://github.com/AquaOH/nonebot-plugin-mcmotd",
    config=Config,
    supported_adapters={"~onebot.v11"},
    extra={
        "author": "AquaOH",
        "keywords": ["minecraft", "motd", "server", "status"],
        "features": [
            "Minecraft服务器状态查询",
            "图片生成展示",
        ]
    }
)

from . import commands