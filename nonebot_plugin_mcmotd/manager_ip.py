import aiosqlite
import os
from typing import List, Optional, NamedTuple
from nonebot import logger
from .config import plugin_db_path

class MinecraftServer(NamedTuple):
    id: int
    ip_port: str
    tag: str
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
                        ip_port TEXT UNIQUE NOT NULL,
                        tag TEXT NOT NULL,
                        display_order INTEGER NOT NULL DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await db.commit()
                logger.info("数据库初始化成功")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

    async def add_server(self, ip_port: str, tag: str) -> tuple[bool, str]:
        try:
            await self.init_database()

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT tag FROM minecraft_servers WHERE ip_port = ?", (ip_port,)) as cursor:
                    existing = await cursor.fetchone()

                if existing:
                    return False, f"服务器 {ip_port} 已存在，标签为：{existing[0]}"

                async with db.execute("SELECT COALESCE(MAX(display_order), 0) FROM minecraft_servers") as cursor:
                    max_order_row = await cursor.fetchone()
                    next_order = (max_order_row[0] if max_order_row else 0) + 1

                await db.execute("INSERT INTO minecraft_servers (ip_port, tag, display_order) VALUES (?, ?, ?)", (ip_port, tag, next_order))
                await db.commit()

                logger.info(f"成功添加服务器：{ip_port} - {tag}")
                return True, f"成功添加服务器：\nIP: {ip_port}\n标签: {tag}"

        except Exception as e:
            logger.error(f"添加服务器失败：{e}")
            return False, f"添加服务器失败：{str(e)}"

    async def delete_server(self, ip_port: str) -> tuple[bool, str]:
        try:
            await self.init_database()

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT tag, display_order FROM minecraft_servers WHERE ip_port = ?", (ip_port,)) as cursor:
                    server_to_delete = await cursor.fetchone()

                if not server_to_delete:
                    return False, f"服务器 {ip_port} 不存在"

                deleted_order = server_to_delete[1]
                await db.execute("DELETE FROM minecraft_servers WHERE ip_port = ?", (ip_port,))
                await db.execute("UPDATE minecraft_servers SET display_order = display_order - 1 WHERE display_order > ?", (deleted_order,))
                await db.commit()

                logger.info(f"成功删除服务器：{ip_port}")
                return True, f"成功删除服务器：{ip_port} ({server_to_delete[0]})"

        except Exception as e:
            logger.error(f"删除服务器失败：{e}")
            return False, f"删除服务器失败：{str(e)}"

    async def clear_all_servers(self) -> tuple[bool, str]:
        try:
            await self.init_database()

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT COUNT(*) FROM minecraft_servers") as cursor:
                    count_row = await cursor.fetchone()
                    current_count = count_row[0] if count_row else 0

                if current_count == 0:
                    return False, "数据库中没有服务器可删除"

                await db.execute("DELETE FROM minecraft_servers")
                await db.commit()

                await db.execute("DELETE FROM sqlite_sequence WHERE name='minecraft_servers'")
                await db.commit()

                logger.warning(f"已清空所有服务器，共删除 {current_count} 个")
                return True, f"已清空所有服务器（共删除 {current_count} 个）"

        except Exception as e:
            logger.error(f"清空服务器失败：{e}")
            return False, f"清空服务器失败：{str(e)}"

    async def get_all_servers(self) -> List[MinecraftServer]:
        try:
            await self.init_database()

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT id, ip_port, tag, display_order FROM minecraft_servers ORDER BY display_order, id") as cursor:
                    rows = await cursor.fetchall()
                    return [MinecraftServer(id=row[0], ip_port=row[1], tag=row[2], display_order=row[3]) for row in rows]

        except Exception as e:
            logger.error(f"获取服务器列表失败：{e}")
            return []

    async def get_server_by_ip(self, ip_port: str) -> Optional[MinecraftServer]:
        try:
            await self.init_database()

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT id, ip_port, tag, display_order FROM minecraft_servers WHERE ip_port = ?", (ip_port,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return MinecraftServer(id=row[0], ip_port=row[1], tag=row[2], display_order=row[3])
                    return None

        except Exception as e:
            logger.error(f"查询服务器失败：{e}")
            return None

    async def allocate_server_order(self, ip_port: str, target_position: int) -> tuple[bool, str]:
        try:
            await self.init_database()

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT id, tag, display_order FROM minecraft_servers WHERE ip_port = ?", (ip_port,)) as cursor:
                    server = await cursor.fetchone()

                if not server:
                    return False, f"服务器 {ip_port} 不存在"

                async with db.execute("SELECT COUNT(*) FROM minecraft_servers") as cursor:
                    total_count_row = await cursor.fetchone()
                    total_count = total_count_row[0] if total_count_row else 0

                if target_position < 1 or target_position > total_count:
                    return False, f"位置必须在 1 到 {total_count} 之间"

                server_id, server_tag, current_order = server

                if current_order == target_position:
                    return False, f"服务器 {server_tag} 已经在位置 {target_position}"

                if current_order < target_position:
                    await db.execute("UPDATE minecraft_servers SET display_order = display_order - 1 WHERE display_order > ? AND display_order <= ?", (current_order, target_position))
                else:
                    await db.execute("UPDATE minecraft_servers SET display_order = display_order + 1 WHERE display_order >= ? AND display_order < ?", (target_position, current_order))

                await db.execute("UPDATE minecraft_servers SET display_order = ? WHERE id = ?", (target_position, server_id))
                await db.commit()

                logger.info(f"成功将服务器 {ip_port} 移动到位置 {target_position}")
                return True, f"成功将服务器 {server_tag} 移动到位置 {target_position}"

        except Exception as e:
            logger.error(f"调整服务器顺序失败：{e}")
            return False, f"调整服务器顺序失败：{str(e)}"

    async def swap_server_order(self, ip_port_a: str, ip_port_b: str) -> tuple[bool, str]:
        try:
            await self.init_database()

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT id, tag, display_order FROM minecraft_servers WHERE ip_port = ?", (ip_port_a,)) as cursor:
                    server_a = await cursor.fetchone()

                async with db.execute("SELECT id, tag, display_order FROM minecraft_servers WHERE ip_port = ?", (ip_port_b,)) as cursor:
                    server_b = await cursor.fetchone()

                if not server_a:
                    return False, f"服务器 {ip_port_a} 不存在"
                if not server_b:
                    return False, f"服务器 {ip_port_b} 不存在"

                id_a, tag_a, order_a = server_a
                id_b, tag_b, order_b = server_b

                await db.execute("UPDATE minecraft_servers SET display_order = ? WHERE id = ?", (order_b, id_a))
                await db.execute("UPDATE minecraft_servers SET display_order = ? WHERE id = ?", (order_a, id_b))
                await db.commit()

                logger.info(f"成功交换服务器 {ip_port_a} 和 {ip_port_b} 的顺序")
                return True, f"成功交换 {tag_a} 和 {tag_b} 的显示顺序"

        except Exception as e:
            logger.error(f"交换服务器顺序失败：{e}")
            return False, f"交换服务器顺序失败：{str(e)}"

server_manager = ServerManager()

async def add_server(ip_port: str, tag: str) -> tuple[bool, str]:
    return await server_manager.add_server(ip_port, tag)

async def delete_server(ip_port: str) -> tuple[bool, str]:
    return await server_manager.delete_server(ip_port)

async def clear_all_servers() -> tuple[bool, str]:
    return await server_manager.clear_all_servers()

async def get_all_servers() -> List[MinecraftServer]:
    return await server_manager.get_all_servers()

async def get_server_by_ip(ip_port: str) -> Optional[MinecraftServer]:
    return await server_manager.get_server_by_ip(ip_port)

async def allocate_server_order(ip_port: str, target_position: int) -> tuple[bool, str]:
    return await server_manager.allocate_server_order(ip_port, target_position)

async def swap_server_order(ip_port_a: str, ip_port_b: str) -> tuple[bool, str]:
    return await server_manager.swap_server_order(ip_port_a, ip_port_b)