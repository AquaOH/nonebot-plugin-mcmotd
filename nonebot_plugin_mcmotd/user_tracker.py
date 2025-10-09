import aiosqlite
from typing import Optional
from datetime import datetime
from nonebot import logger, on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from .config import plugin_config, plugin_db_path

class UserActivityTracker:
    def __init__(self):
        self.db_path = str(plugin_db_path)
    
    async def init_database(self):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS user_group_activity (
                        user_id TEXT NOT NULL,
                        group_id TEXT NOT NULL,
                        last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
                        message_count INTEGER DEFAULT 1,
                        PRIMARY KEY (user_id, group_id)
                    )
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_activity 
                    ON user_group_activity(user_id, last_active DESC)
                """)
                
                await db.commit()
                logger.debug("用户活跃追踪表初始化成功")
        except Exception as e:
            logger.error(f"用户活跃追踪表初始化失败: {e}")
    
    async def update_activity(self, user_id: str, group_id: str):
        if not plugin_config.mc_motd_track_user_activity:
            return
        
        if not plugin_config.mc_motd_multi_group_mode:
            return
        
        try:
            await self.init_database()
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO user_group_activity (user_id, group_id, last_active, message_count)
                    VALUES (?, ?, ?, 1)
                    ON CONFLICT(user_id, group_id) DO UPDATE SET
                        last_active = ?,
                        message_count = message_count + 1
                """, (user_id, group_id, datetime.now(), datetime.now()))
                
                await db.commit()
                logger.debug(f"更新用户 {user_id} 在群 {group_id} 的活跃记录")
        except Exception as e:
            logger.error(f"更新用户活跃记录失败: {e}")
    
    async def get_user_last_active_group(self, user_id: str) -> Optional[str]:
        try:
            await self.init_database()
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT group_id FROM user_group_activity
                    WHERE user_id = ?
                    ORDER BY last_active DESC
                    LIMIT 1
                """, (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        logger.debug(f"用户 {user_id} 最近活跃群: {row[0]}")
                        return row[0]
                    else:
                        logger.debug(f"未找到用户 {user_id} 的活跃记录")
                        return None
        except Exception as e:
            logger.error(f"查询用户活跃群失败: {e}")
            return None

user_activity_tracker = UserActivityTracker()

if plugin_config.mc_motd_multi_group_mode and plugin_config.mc_motd_track_user_activity:
    track_matcher = on_message(priority=1, block=False)
    
    @track_matcher.handle()
    async def track_group_activity(event: GroupMessageEvent):
        await user_activity_tracker.update_activity(
            str(event.user_id),
            str(event.group_id)
        )