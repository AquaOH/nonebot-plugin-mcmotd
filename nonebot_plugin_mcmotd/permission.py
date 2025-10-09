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
        logger.debug(f"NoneBot超级管理员 {user_id} 执行管理操作")
        return True
    
    plugin_superusers = plugin_config.mc_motd_superusers
    if user_id in plugin_superusers:
        logger.debug(f"插件超级管理员 {user_id} 执行管理操作")
        return True
    
    return False

def can_self_manage_personal_scope(event: Event, scope: str) -> bool:
    if not isinstance(event, PrivateMessageEvent):
        return False
    
    user_id = str(event.user_id)
    
    if scope == f"private_friend_{user_id}":
        logger.info(f"用户 {user_id} 管理自己的好友私聊服务器列表")
        return True
    
    if scope == f"private_temp_{user_id}":
        logger.info(f"用户 {user_id} 管理自己的临时会话服务器列表")
        return True
    
    return False

def is_admin(event: Event, scope: str = "global") -> bool:
    if is_superuser(event):
        return True
    
    if plugin_config.mc_motd_multi_group_mode:
        if isinstance(event, GroupMessageEvent):
            group_id = str(event.group_id)
            
            if scope == f"group_{group_id}":
                if is_group_admin(event):
                    logger.info(f"群管理员 {event.user_id} 管理群 {group_id} 的服务器")
                    return True
            
            if scope.startswith("cluster_"):
                cluster_name = scope.replace("cluster_", "")
                cluster_groups = plugin_config.mc_motd_group_clusters.get(cluster_name, [])
                
                if group_id in cluster_groups:
                    if is_group_admin(event):
                        logger.info(f"群管理员 {event.user_id} 管理群组 {cluster_name} 的服务器")
                        return True
        
        if isinstance(event, PrivateMessageEvent):
            if can_self_manage_personal_scope(event, scope):
                return True
    
    else:
        if is_group_admin(event):
            logger.info(f"群管理员 {event.user_id} 执行管理操作（传统模式）")
            return True
    
    return False