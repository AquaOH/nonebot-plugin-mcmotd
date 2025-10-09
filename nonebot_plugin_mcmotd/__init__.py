from nonebot.plugin import PluginMetadata

from .config import Config

__version__ = "2.0.0"

__plugin_meta__ = PluginMetadata(
    name="Minecraft MOTD 查询",
    description="查询多个 Minecraft 服务器状态并生成在一张图片上展示（支持多群隔离）",
    usage=(
        "用户命令（任何人可用）：\n"
        "/motd - 查询所有服务器状态\n"
        "/motd --detail - 显示详细信息包括玩家列表\n\n"
        "/motd help - 显示此帮助信息\n\n"
        "管理员命令（超级管理员或群管理员）：\n"
        "/motd add ip:port 标签 - 添加服务器\n"
        "/motd del ip:port - 删除指定服务器\n"
        "/motd del -rf - 删除所有服务器\n"
        "/motd render allocate ip:port 位置 - 调整服务器显示顺序\n"
        "/motd render swap ip1:port ip2:port - 交换两个服务器顺序\n\n"
        "超级管理员专用命令：\n"
        "/motd scope list - 查看所有作用域列表\n"
        "/motd --scope=xxx - 查看指定作用域的服务器\n"
        "/motd --scope=all - 查看所有作用域的服务器（合并显示）\n"
        "/motd add --scope=xxx ip:port 标签 - 向指定作用域添加服务器\n"
        "/motd add --scope=all ip:port 标签 - 向所有作用域添加服务器\n"
        "/motd del --scope=xxx ip:port - 从指定作用域删除服务器\n"
        "/motd del --scope=all -rf - 删除所有作用域的所有服务器\n\n"
        "管理员权限包括:\n"
        "- 群管理员或群主 (需开启群管理员权限)\n"
        "- 个人列表模式下的用户本人\n\n"
        "超级管理员权限包括：\n"
        "- NoneBot 超级管理员 (SUPERUSERS)\n"
        "- 插件超级管理员 (MC_MOTD_SUPERUSERS)"
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