from typing import Optional
from nonebot import logger
from nonebot.adapters.onebot.v11 import Event, GroupMessageEvent, PrivateMessageEvent
from .config import plugin_config
from .user_tracker import user_activity_tracker

class ScopeResolver:
    def __init__(self):
        self.config = plugin_config
    
    async def get_scope(self, event: Event) -> Optional[str]:
        if not self.config.mc_motd_multi_group_mode:
            return "global"
        
        if isinstance(event, GroupMessageEvent):
            return await self._resolve_group_scope(event)
        
        if isinstance(event, PrivateMessageEvent):
            return await self._resolve_private_scope(event)
        
        logger.warning(f"未知消息类型: {type(event)}, 降级为全局作用域")
        return "global"
    
    async def _resolve_group_scope(self, event: GroupMessageEvent) -> str:
        group_id = str(event.group_id)
        
        for cluster_name, group_ids in self.config.mc_motd_group_clusters.items():
            if group_id in group_ids:
                logger.debug(f"群 {group_id} 属于群组 {cluster_name}")
                return f"cluster_{cluster_name}"
        
        logger.debug(f"群 {group_id} 使用独立作用域")
        return f"group_{group_id}"
    
    async def _resolve_private_scope(self, event: PrivateMessageEvent) -> Optional[str]:
        user_id = str(event.user_id)
        sub_type = event.sub_type
        
        if sub_type == "friend":
            strategy = self.config.mc_motd_private_friend_strategy
            logger.debug(f"好友私聊 {user_id}, 策略: {strategy}")
            
            if strategy == "disabled":
                return None
            elif strategy == "global":
                return "global"
            elif strategy == "personal":
                return f"private_friend_{user_id}"
            else:
                logger.warning(f"未知的好友私聊策略: {strategy}, 降级为 global")
                return "global"
        
        elif sub_type == "group":
            strategy = self.config.mc_motd_private_group_temp_strategy
            logger.debug(f"群临时会话 {user_id}, 策略: {strategy}")
            
            if strategy == "disabled":
                return None
            elif strategy == "global":
                return "global"
            elif strategy == "personal":
                return f"private_temp_{user_id}"
            elif strategy == "follow_group":
                return await self._resolve_follow_group(event)
            else:
                logger.warning(f"未知的群临时会话策略: {strategy}, 降级为 global")
                return "global"
        
        else:
            logger.warning(f"未知私聊子类型: {sub_type}, 降级为 global")
            return "global"
    
    async def _resolve_follow_group(self, event: PrivateMessageEvent) -> str:
        user_id = str(event.user_id)
        
        source_group_id = await user_activity_tracker.get_user_last_active_group(user_id)
        
        if source_group_id:
            logger.info(f"用户 {user_id} 的来源群: {source_group_id}")
            
            for cluster_name, group_ids in self.config.mc_motd_group_clusters.items():
                if source_group_id in group_ids:
                    logger.debug(f"来源群 {source_group_id} 属于群组 {cluster_name}")
                    return f"cluster_{cluster_name}"
            
            return f"group_{source_group_id}"
        else:
            fallback = self.config.mc_motd_follow_group_fallback
            logger.warning(f"无法确定用户 {user_id} 的来源群，使用降级策略: {fallback}")
            
            if fallback == "personal":
                return f"private_temp_{user_id}"
            elif fallback == "global":
                return "global"
            else:
                return f"private_temp_{user_id}"
    
    def get_scope_display_name(self, scope: str) -> str:
        if scope == "all":
            return "所有作用域"
        elif scope == "global":
            return "全局"
        elif scope.startswith("group_"):
            group_id = scope.replace("group_", "")
            return f"群 {group_id}"
        elif scope.startswith("cluster_"):
            cluster_name = scope.replace("cluster_", "")
            return f"群组 {cluster_name}"
        elif scope.startswith("private_friend_"):
            user_id = scope.replace("private_friend_", "")
            return f"好友 {user_id} 的个人列表"
        elif scope.startswith("private_temp_"):
            user_id = scope.replace("private_temp_", "")
            return f"用户 {user_id} 的临时列表"
        else:
            return scope

scope_resolver = ScopeResolver()