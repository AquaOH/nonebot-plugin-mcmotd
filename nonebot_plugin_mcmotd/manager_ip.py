import aiosqlite
import os
from typing import List, Optional, NamedTuple
from nonebot import logger
from .config import plugin_config, plugin_db_path

class MinecraftServer(NamedTuple):
    id: int
    ip_port: str
    tag: str
    scope: str
    display_order: int

class ServerManager:
    def __init__(self):
        self.db_path = str(plugin_db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    async def init_database(self):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS minecraft_servers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ip_port TEXT NOT NULL,
                        tag TEXT NOT NULL,
                        scope TEXT NOT NULL DEFAULT 'global',
                        display_order INTEGER NOT NULL DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(ip_port, scope)
                    )
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_scope 
                    ON minecraft_servers(scope, display_order)
                """)
                
                await db.commit()
                logger.info("数据库初始化成功")
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    async def get_server_count(self, scope: str = "global") -> int:
        try:
            await self.init_database()
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT COUNT(*) FROM minecraft_servers WHERE scope = ?",
                    (scope,)
                ) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            logger.error(f"获取服务器数量失败：{e}")
            return 0
    
    async def check_personal_limit(self, scope: str) -> tuple[bool, str]:
        if not (scope.startswith("private_friend_") or scope.startswith("private_temp_")):
            return True, ""
        
        limit = plugin_config.mc_motd_personal_server_limit
        
        if limit <= 0:
            return True, ""
        
        current_count = await self.get_server_count(scope)
        
        if current_count >= limit:
            return False, f"已达到个人服务器数量上限（{limit}个）"
        
        return True, ""

    async def add_server(self, ip_port: str, tag: str, scope: str = "global") -> tuple[bool, str]:
        try:
            await self.init_database()
            
            can_add, limit_msg = await self.check_personal_limit(scope)
            if not can_add:
                return False, limit_msg

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT tag FROM minecraft_servers WHERE ip_port = ? AND scope = ?", 
                    (ip_port, scope)
                ) as cursor:
                    existing = await cursor.fetchone()

                if existing:
                    return False, f"服务器 {ip_port} 在当前作用域已存在，标签为：{existing[0]}"

                async with db.execute(
                    "SELECT COALESCE(MAX(display_order), 0) FROM minecraft_servers WHERE scope = ?",
                    (scope,)
                ) as cursor:
                    max_order_row = await cursor.fetchone()
                    next_order = (max_order_row[0] if max_order_row else 0) + 1

                await db.execute(
                    "INSERT INTO minecraft_servers (ip_port, tag, scope, display_order) VALUES (?, ?, ?, ?)",
                    (ip_port, tag, scope, next_order)
                )
                await db.commit()

                logger.info(f"成功添加服务器：{ip_port} - {tag} (scope: {scope})")
                return True, f"成功添加服务器：\nIP: {ip_port}\n标签: {tag}"

        except Exception as e:
            logger.error(f"添加服务器失败：{e}")
            return False, f"添加服务器失败：{str(e)}"

    async def delete_server(self, ip_port: str, scope: str = "global") -> tuple[bool, str]:
        try:
            await self.init_database()

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT tag, display_order FROM minecraft_servers WHERE ip_port = ? AND scope = ?",
                    (ip_port, scope)
                ) as cursor:
                    server_to_delete = await cursor.fetchone()

                if not server_to_delete:
                    return False, f"服务器 {ip_port} 在当前作用域不存在"

                deleted_order = server_to_delete[1]
                
                await db.execute(
                    "DELETE FROM minecraft_servers WHERE ip_port = ? AND scope = ?",
                    (ip_port, scope)
                )
                
                await db.execute(
                    "UPDATE minecraft_servers SET display_order = display_order - 1 WHERE scope = ? AND display_order > ?",
                    (scope, deleted_order)
                )
                
                await db.commit()

                logger.info(f"成功删除服务器：{ip_port} (scope: {scope})")
                return True, f"成功删除服务器：{ip_port} ({server_to_delete[0]})"

        except Exception as e:
            logger.error(f"删除服务器失败：{e}")
            return False, f"删除服务器失败：{str(e)}"

    async def clear_all_servers(self, scope: str = "global") -> tuple[bool, str]:
        try:
            await self.init_database()

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT COUNT(*) FROM minecraft_servers WHERE scope = ?",
                    (scope,)
                ) as cursor:
                    count_row = await cursor.fetchone()
                    current_count = count_row[0] if count_row else 0

                if current_count == 0:
                    return False, "当前作用域没有服务器可删除"

                await db.execute(
                    "DELETE FROM minecraft_servers WHERE scope = ?",
                    (scope,)
                )
                await db.commit()

                logger.warning(f"已清空作用域 {scope} 的所有服务器，共删除 {current_count} 个")
                return True, f"已清空当前作用域的所有服务器（共删除 {current_count} 个）"

        except Exception as e:
            logger.error(f"清空服务器失败：{e}")
            return False, f"清空服务器失败：{str(e)}"

    async def get_all_servers(self, scope: str = "global") -> List[MinecraftServer]:
        try:
            await self.init_database()

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT id, ip_port, tag, scope, display_order FROM minecraft_servers WHERE scope = ? ORDER BY display_order, id",
                    (scope,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [
                        MinecraftServer(
                            id=row[0],
                            ip_port=row[1],
                            tag=row[2],
                            scope=row[3],
                            display_order=row[4]
                        ) for row in rows
                    ]

        except Exception as e:
            logger.error(f"获取服务器列表失败：{e}")
            return []

    async def get_server_by_ip(self, ip_port: str, scope: str = "global") -> Optional[MinecraftServer]:
        try:
            await self.init_database()

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT id, ip_port, tag, scope, display_order FROM minecraft_servers WHERE ip_port = ? AND scope = ?",
                    (ip_port, scope)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return MinecraftServer(
                            id=row[0],
                            ip_port=row[1],
                            tag=row[2],
                            scope=row[3],
                            display_order=row[4]
                        )
                    return None

        except Exception as e:
            logger.error(f"查询服务器失败：{e}")
            return None

    async def allocate_server_order(self, ip_port: str, target_position: int, scope: str = "global") -> tuple[bool, str]:
        try:
            await self.init_database()

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT id, tag, display_order FROM minecraft_servers WHERE ip_port = ? AND scope = ?",
                    (ip_port, scope)
                ) as cursor:
                    server = await cursor.fetchone()

                if not server:
                    return False, f"服务器 {ip_port} 在当前作用域不存在"

                async with db.execute(
                    "SELECT COUNT(*) FROM minecraft_servers WHERE scope = ?",
                    (scope,)
                ) as cursor:
                    total_count_row = await cursor.fetchone()
                    total_count = total_count_row[0] if total_count_row else 0

                if target_position < 1 or target_position > total_count:
                    return False, f"位置必须在 1 到 {total_count} 之间"

                server_id, server_tag, current_order = server

                if current_order == target_position:
                    return False, f"服务器 {server_tag} 已经在位置 {target_position}"

                if current_order < target_position:
                    await db.execute(
                        "UPDATE minecraft_servers SET display_order = display_order - 1 WHERE scope = ? AND display_order > ? AND display_order <= ?",
                        (scope, current_order, target_position)
                    )
                else:
                    await db.execute(
                        "UPDATE minecraft_servers SET display_order = display_order + 1 WHERE scope = ? AND display_order >= ? AND display_order < ?",
                        (scope, target_position, current_order)
                    )

                await db.execute(
                    "UPDATE minecraft_servers SET display_order = ? WHERE id = ?",
                    (target_position, server_id)
                )
                await db.commit()

                logger.info(f"成功将服务器 {ip_port} 移动到位置 {target_position} (scope: {scope})")
                return True, f"成功将服务器 {server_tag} 移动到位置 {target_position}"

        except Exception as e:
            logger.error(f"调整服务器顺序失败：{e}")
            return False, f"调整服务器顺序失败：{str(e)}"

    async def swap_server_order(self, ip_port_a: str, ip_port_b: str, scope: str = "global") -> tuple[bool, str]:
        try:
            await self.init_database()

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT id, tag, display_order FROM minecraft_servers WHERE ip_port = ? AND scope = ?",
                    (ip_port_a, scope)
                ) as cursor:
                    server_a = await cursor.fetchone()

                async with db.execute(
                    "SELECT id, tag, display_order FROM minecraft_servers WHERE ip_port = ? AND scope = ?",
                    (ip_port_b, scope)
                ) as cursor:
                    server_b = await cursor.fetchone()

                if not server_a:
                    return False, f"服务器 {ip_port_a} 在当前作用域不存在"
                if not server_b:
                    return False, f"服务器 {ip_port_b} 在当前作用域不存在"

                id_a, tag_a, order_a = server_a
                id_b, tag_b, order_b = server_b

                await db.execute(
                    "UPDATE minecraft_servers SET display_order = ? WHERE id = ?",
                    (order_b, id_a)
                )
                await db.execute(
                    "UPDATE minecraft_servers SET display_order = ? WHERE id = ?",
                    (order_a, id_b)
                )
                await db.commit()

                logger.info(f"成功交换服务器 {ip_port_a} 和 {ip_port_b} 的顺序 (scope: {scope})")
                return True, f"成功交换 {tag_a} 和 {tag_b} 的显示顺序"

        except Exception as e:
            logger.error(f"交换服务器顺序失败：{e}")
            return False, f"交换服务器顺序失败：{str(e)}"

    async def get_all_existing_scopes(self) -> List[str]:
        try:
            await self.init_database()
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT DISTINCT scope FROM minecraft_servers ORDER BY scope"
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"获取作用域列表失败：{e}")
            return []

server_manager = ServerManager()

async def add_server(ip_port: str, tag: str, scope: str = "global") -> tuple[bool, str]:
    return await server_manager.add_server(ip_port, tag, scope)

async def delete_server(ip_port: str, scope: str = "global") -> tuple[bool, str]:
    return await server_manager.delete_server(ip_port, scope)

async def clear_all_servers(scope: str = "global") -> tuple[bool, str]:
    return await server_manager.clear_all_servers(scope)

async def get_all_servers(scope: str = "global") -> List[MinecraftServer]:
    return await server_manager.get_all_servers(scope)

async def get_server_by_ip(ip_port: str, scope: str = "global") -> Optional[MinecraftServer]:
    return await server_manager.get_server_by_ip(ip_port, scope)

async def allocate_server_order(ip_port: str, target_position: int, scope: str = "global") -> tuple[bool, str]:
    return await server_manager.allocate_server_order(ip_port, target_position, scope)

async def swap_server_order(ip_port_a: str, ip_port_b: str, scope: str = "global") -> tuple[bool, str]:
    return await server_manager.swap_server_order(ip_port_a, ip_port_b, scope)

async def get_server_count(scope: str = "global") -> int:
    return await server_manager.get_server_count(scope)

async def get_all_existing_scopes() -> List[str]:
    return await server_manager.get_all_existing_scopes()