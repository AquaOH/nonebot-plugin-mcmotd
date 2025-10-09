from nonebot.plugin import PluginMetadata

from .config import Config

__version__ = "1.0.3"

__plugin_meta__ = PluginMetadata(
    name="Minecraft MOTD 查询",
    description="查询多个 Minecraft 服务器状态并生成在一张图片上展示（支持多群隔离）",
    usage=(
        "用户命令:\n"
        "/motd - 查询所有服务器状态\n"
        "/motd --detail - 显示详细信息包括玩家列表\n\n"
        "/motd help - 显示帮助信息\n\n"
        "管理员命令:\n"
        "/motd add ip:port 标签 - 添加服务器\n"
        "/motd del ip:port - 删除服务器\n"
        "/motd del -rf - 删除所有服务器\n"
        "/motd render allocate ip:port 位置 - 调整服务器显示顺序\n"
        "/motd render swap ip1:port ip2:port - 交换两个服务器顺序\n"
        "管理员权限包括:\n"
        "- NoneBot 超级管理员 (SUPERUSERS)\n"
        "- 插件超级管理员 (MC_MOTD_SUPERUSERS)\n"
        "- 群管理员或群主 (需开启群管理员权限)\n"
        "- 个人列表模式下的用户本人"
    ),
    type="application",
    homepage="https://github.com/AquaOH/nonebot-plugin-mcmotd",
    config=Config,
    supported_adapters={"~onebot.v11"},
    extra={
        "author": "AquaOH",
        "keywords": ["minecraft", "motd", "server", "status", "multi-group"],
        "features": [
            "Minecraft服务器状态查询",
            "图片生成展示",
            "多群聊隔离支持",
            "私聊策略配置",
        ]
    }
)

from . import commands
from . import user_tracker