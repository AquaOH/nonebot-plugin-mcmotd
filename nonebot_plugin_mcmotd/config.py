from pydantic import BaseModel, Field
from typing import List, Optional
from nonebot import get_plugin_config, require

# 引入localstore插件
require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

class Config(BaseModel):
    mc_motd_superusers: List[str] = []
    mc_motd_timeout: float = Field(default=5.0, gt=0)
    mc_motd_filter_bots: bool = True
    mc_motd_bot_names: List[str] = ["Anonymous Player"]
    mc_motd_image_width: int = Field(default=1000, ge=400)
    mc_motd_item_height: int = Field(default=160, ge=100)
    mc_motd_margin: int = Field(default=30, ge=10)
    mc_motd_allowed_groups: List[str] = [] 
    mc_motd_allow_private: bool = True
    mc_motd_group_admin_permission: bool = True  # 新增：群管理员权限配置
    mc_motd_title: str = "Minecraft 服务器状态"
    mc_motd_custom_font: str = ""  # 自定义字体完整路径

# 获取配置实例并导出
plugin_config = get_plugin_config(Config)

# 获取插件数据目录
plugin_data_dir = store.get_plugin_data_dir()
plugin_db_path = plugin_data_dir / "mcmotd_serverlist.db"