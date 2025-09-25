from nonebot import logger, get_driver
from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent, PrivateMessageEvent
from .config import plugin_config

driver = get_driver()
global_config = driver.config
nonebot_superusers = getattr(global_config, 'superusers', set())

def get_user_id(event: Event) -> str:
    if isinstance(event, (GroupMessageEvent, PrivateMessageEvent)):
        return str(event.user_id)
    return ""

def is_group_admin(event: Event) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    
    if not plugin_config.mc_motd_group_admin_permission:
        return False
    
    return event.sender.role in ['admin', 'owner']

def is_superuser(event: Event) -> bool:
    user_id = get_user_id(event)
    
    if not user_id:
        return False
    
    if user_id in nonebot_superusers:
        logger.info(f"NoneBot超级管理员 {user_id} 执行管理操作")
        return True
    
    plugin_superusers = plugin_config.mc_motd_superusers
    
    if user_id in plugin_superusers:
        logger.info(f"插件超级管理员 {user_id} 执行管理操作")
        return True
    
    return False

def is_admin(event: Event) -> bool:
    if is_superuser(event):
        return True
    
    if is_group_admin(event):
        logger.info(f"群管理员 {event.user_id} 执行管理操作")
        return True
    
    return False

def check_admin_permission(event: Event) -> bool:
    return is_admin(event)