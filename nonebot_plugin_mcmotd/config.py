from pydantic import BaseModel, Field, field_validator
from typing import List, Dict
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
    mc_motd_enable_compression: bool = False
    mc_motd_compression_quality: int = Field(80, ge=1, le=100)
    
    mc_motd_multi_group_mode: bool = False
    mc_motd_group_clusters: Dict[str, List[str]] = {}
    mc_motd_private_friend_strategy: str = "personal"
    mc_motd_private_group_temp_strategy: str = "follow_group"
    mc_motd_track_user_activity: bool = True
    mc_motd_follow_group_fallback: str = "personal"
    mc_motd_personal_server_limit: int = 10
    
    mc_motd_scope_titles: Dict[str, str] = {}

    @field_validator('mc_motd_group_clusters')
    @classmethod
    def validate_no_all_cluster(cls, v):
        if 'all' in v:
            raise ValueError("Scope name 'all' is reserved and cannot be used in mc_motd_group_clusters")
        return v

plugin_config = get_plugin_config(Config)
plugin_data_dir = store.get_plugin_data_dir()
plugin_db_path = plugin_data_dir / "mcmotd_serverlist.db"