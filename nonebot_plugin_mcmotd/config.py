from pydantic import BaseModel, Field
from typing import List
from nonebot import get_plugin_config, require

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

class Config(BaseModel):
    mc_motd_superusers: List[str] = []
    mc_motd_timeout: float = Field(5.0, gt=0)
    mc_motd_filter_bots: bool = True
    mc_motd_bot_names: List[str] = ["Anonymous Player"]
    mc_motd_bot_patterns: List[str] = [
        r"^player_\d+$",
        r"^bot_\d+$",
        r"^fake_\d+$",
        r"^\[Bot\]",
        r"^\[Fake\]"
    ]
    mc_motd_image_width: int = Field(1000, ge=400)
    mc_motd_item_height: int = Field(160, ge=100)
    mc_motd_margin: int = Field(30, ge=10)
    mc_motd_allowed_groups: List[str] = []
    mc_motd_allow_private: bool = True
    mc_motd_group_admin_permission: bool = True
    mc_motd_title: str = "Minecraft 服务器状态"
    mc_motd_custom_font: str = ""
    mc_motd_enable_compression: bool = True
    mc_motd_compression_quality: int = Field(80, ge=1, le=100)

plugin_config = get_plugin_config(Config)
plugin_data_dir = store.get_plugin_data_dir()
plugin_db_path = plugin_data_dir / "mcmotd_serverlist.db"