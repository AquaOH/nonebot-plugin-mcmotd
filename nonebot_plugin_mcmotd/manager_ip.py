import aiosqlite
import os
from pathlib import Path
from typing import List, Optional, NamedTuple
from nonebot import logger
from .config import plugin_config, plugin_db_path


class MinecraftServer(NamedTuple):
    id: int
    ip_port: str
    tag: str


class ServerManager:
    def __init__(self):
        self.db_path = str(plugin_db_path)
        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    async def init_database(self):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS minecraft_servers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ip_port TEXT UNIQUE NOT NULL,
                        tag TEXT NOT NULL,
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
                # 检查服务器是否已存在
                async with db.execute(
                        "SELECT tag FROM minecraft_servers WHERE ip_port = ?",
                        (ip_port,)
                ) as cursor:
                    existing = await cursor.fetchone()

                if existing:
                    return False, f"服务器 {ip_port} 已存在，标签为：{existing[0]}"

                # 添加新服务器
                await db.execute(
                    "INSERT INTO minecraft_servers (ip_port, tag) VALUES (?, ?)",
                    (ip_port, tag)
                )
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
                # 查找要删除的服务器
                async with db.execute(
                        "SELECT tag FROM minecraft_servers WHERE ip_port = ?",
                        (ip_port,)
                ) as cursor:
                    server_to_delete = await cursor.fetchone()

                if not server_to_delete:
                    return False, f"服务器 {ip_port} 不存在"

                # 删除服务器
                await db.execute(
                    "DELETE FROM minecraft_servers WHERE ip_port = ?",
                    (ip_port,)
                )
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
                # 获取当前服务器数量
                async with db.execute("SELECT COUNT(*) FROM minecraft_servers") as cursor:
                    count_row = await cursor.fetchone()
                    current_count = count_row[0] if count_row else 0

                if current_count == 0:
                    return False, "数据库中没有服务器可删除"

                # 删除所有服务器
                await db.execute("DELETE FROM minecraft_servers")
                await db.commit()

                # 重置自增ID
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
                async with db.execute(
                        "SELECT id, ip_port, tag FROM minecraft_servers ORDER BY id"
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [MinecraftServer(id=row[0], ip_port=row[1], tag=row[2]) for row in rows]

        except Exception as e:
            logger.error(f"获取服务器列表失败：{e}")
            return []

    async def get_server_by_ip(self, ip_port: str) -> Optional[MinecraftServer]:
        try:
            await self.init_database()

            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                        "SELECT id, ip_port, tag FROM minecraft_servers WHERE ip_port = ?",
                        (ip_port,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return MinecraftServer(id=row[0], ip_port=row[1], tag=row[2])
                    return None

        except Exception as e:
            logger.error(f"查询服务器失败：{e}")
            return None


# 创建管理器实例
server_manager = ServerManager()


# 为了向后兼容和简化使用，提供简单的函数接口
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