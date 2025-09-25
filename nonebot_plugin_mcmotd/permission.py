from nonebot import logger, get_driver
from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent, PrivateMessageEvent
from .config import plugin_config

# 获取NoneBot的全局配置中的SUPERUSERS
driver = get_driver()
global_config = driver.config
nonebot_superusers = getattr(global_config, 'superusers', set())


def get_user_id(event: Event) -> str:
    """从事件中提取用户ID"""
    if isinstance(event, (GroupMessageEvent, PrivateMessageEvent)):
        return str(event.user_id)
    return ""


def is_group_admin(event: Event) -> bool:
    """检查用户是否为群管理员或群主"""
    if not isinstance(event, GroupMessageEvent):
        return False
    
    if not plugin_config.mc_motd_group_admin_permission:
        return False
    
    # 检查是否为群主或管理员
    return event.sender.role in ['admin', 'owner']


def is_superuser(event: Event) -> bool:
    """检查用户是否为超级管理员"""
    user_id = get_user_id(event)
    
    if not user_id:
        return False
    
    # 检查NoneBot自带的SUPERUSERS
    if user_id in nonebot_superusers:
        logger.info(f"NoneBot超级管理员 {user_id} 执行管理操作")
        return True
    
    # 检查插件配置中的超级管理员列表
    plugin_superusers = plugin_config.mc_motd_superusers
    
    if user_id in plugin_superusers:
        logger.info(f"插件超级管理员 {user_id} 执行管理操作")
        return True
    
    return False


def is_admin(event: Event) -> bool:
    """检查用户是否有管理权限（超级管理员或群管理员）"""
    # 首先检查是否为超级管理员
    if is_superuser(event):
        return True
    
    # 然后检查是否为群管理员
    if is_group_admin(event):
        logger.info(f"群管理员 {event.user_id} 执行管理操作")
        return True
    
    return False


def check_admin_permission(event: Event) -> bool:
    """检查管理员权限并返回结果（兼容原有代码）"""
    return is_admin(event)