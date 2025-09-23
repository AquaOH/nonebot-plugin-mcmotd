from pydantic import BaseModel, field_validator
from typing import List, Optional


class Config(BaseModel):
    mc_motd_superusers: List[str] = []
    mc_motd_timeout: float = 5.0
    mc_motd_filter_bots: bool = True
    mc_motd_bot_names: List[str] = ["Anonymous Player"]
    mc_motd_image_width: int = 1000
    mc_motd_item_height: int = 160
    mc_motd_margin: int = 30
    mc_motd_db_path: str = "data/minecraft_servers.db"
    mc_motd_allowed_groups: List[str] = [] 
    mc_motd_allow_private: bool = True      
    mc_motd_title: str = "Minecraft 服务器状态"
    
    @field_validator("mc_motd_timeout")
    @classmethod
    def check_timeout(cls, v: float) -> float:
        if v > 0:
            return v
        raise ValueError("mc_motd_timeout must be greater than 0")
    
    @field_validator("mc_motd_image_width")
    @classmethod
    def check_image_width(cls, v: int) -> int:
        if v >= 400:
            return v
        raise ValueError("mc_motd_image_width must be at least 400")
    
    @field_validator("mc_motd_item_height")
    @classmethod
    def check_item_height(cls, v: int) -> int:
        if v >= 100:
            return v
        raise ValueError("mc_motd_item_height must be at least 100")