from nonebot import get_plugin_config, logger
from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent, PrivateMessageEvent
from .config import Config

# 获取插件配置
plugin_config = get_plugin_config(Config)


def get_user_id(event: Event) -> str:
    """从事件中提取用户ID"""
    if isinstance(event, (GroupMessageEvent, PrivateMessageEvent)):
        return str(event.user_id)
    return ""


def is_superuser(event: Event) -> bool:
    """检查用户是否为超级管理员"""
    user_id = get_user_id(event)
    
    if not user_id:
        return False
    
    # 检查配置中的超级管理员列表
    superusers = plugin_config.mc_motd_superusers
    
    if not superusers:
        logger.warning("未配置超级管理员，请在.env文件中设置 MC_MOTD_SUPERUSERS")
        return False
    
    is_super = user_id in superusers
    
    if is_super:
        logger.info(f"超级管理员 {user_id} 执行管理操作")
    else:
        logger.warning(f"用户 {user_id} 尝试执行管理操作但权限不足")
    
    return is_super