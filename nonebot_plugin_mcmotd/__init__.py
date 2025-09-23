"""
NoneBot Minecraft MOTD 插件

用于查询 Minecraft 服务器状态并生成状态图片
"""

__version__ = "1.0.3"

from nonebot.plugin import PluginMetadata, inherit_supported_adapters

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="Minecraft MOTD 查询",
    description="查询 Minecraft 服务器状态并生成图片展示",
    usage=(
        "用户命令:\n"
        "/motd - 查询所有服务器状态\n"
        "/motd --detail - 显示详细信息包括玩家列表\n\n"
        "管理员命令:\n"
        "/motd add ip:port 标签 - 添加服务器\n"
        "/motd del ip:port - 删除服务器\n"
        "/motd del -rf - 删除所有服务器\n"
        "/motd help - 显示帮助信息\n\n"
        "需要在.env文件中配置超级管理员QQ号才能使用管理功能"
    ),
    type="application",
    homepage="https://github.com/AquaOH/nonebot-plugin-mcmotd",
    config=Config,
    supported_adapters={"~onebot.v11"},
    extra={
        "version": __version__,
        "author": "Your Name",
        "keywords": ["minecraft", "motd", "server", "status"],
        "features": [
            "服务器状态查询",
            "图片生成展示", 
            "假人过滤",
            "详细模式显示",
            "权限管理",
            "批量管理"
        ]
    }
)

# 导入命令处理器以确保插件被正确加载
from . import commands  # noqa: E402