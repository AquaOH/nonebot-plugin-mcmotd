import asyncio
import time
import re
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from nonebot import logger

try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False
    logger.warning("dnspython 未安装，无法解析 SRV 记录")

from mcstatus import JavaServer
from mcstatus.address import Address
from mcstatus.pinger import ServerPinger
from mcstatus.protocol.connection import TCPSocketConnection
from .manager_ip import get_all_servers, MinecraftServer
from .config import plugin_config


@dataclass
class ServerStatus:
    # 基本信息
    ip_port: str
    tag: str
    is_online: bool

    # 服务器状态信息
    motd: Optional[str] = None
    motd_clean: Optional[str] = None  # 清理后的MOTD（去除格式代码）
    icon: Optional[str] = None  # base64编码的服务器图标
    version: Optional[str] = None
    protocol: Optional[int] = None

    # 玩家信息
    players_online: Optional[int] = None
    players_max: Optional[int] = None
    players_list: Optional[List[str]] = field(default_factory=list)
    players_list_filtered: Optional[List[str]] = field(default_factory=list)  # 过滤假人后的玩家列表

    # 网络信息
    latency: Optional[float] = None  # 延迟（毫秒）

    # 错误信息
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'ip_port': self.ip_port,
            'tag': self.tag,
            'is_online': self.is_online,
            'motd': self.motd,
            'motd_clean': self.motd_clean,
            'icon': self.icon,
            'version': self.version,
            'protocol': self.protocol,
            'players_online': self.players_online,
            'players_max': self.players_max,
            'players_list': self.players_list,
            'players_list_filtered': self.players_list_filtered,
            'latency': self.latency,
            'error_message': self.error_message
        }


class PlayerFilter:
    def __init__(self):
        self.bot_names = set(plugin_config.mc_motd_bot_names)
        self.filter_enabled = plugin_config.mc_motd_filter_bots
        
    def is_bot_player(self, player_name: str) -> bool:
        if not self.filter_enabled:
            return False
            
        # 检查是否在假人名单中
        if player_name in self.bot_names:
            return True
            
        # 检查是否符合Carpet假人的命名模式
        # Carpet假人通常以特定前缀开头或包含特定关键词
        carpet_patterns = [
            r'^player_\d+$',  # player_1, player_2 等
            r'^bot_',         # bot_ 开头
            r'^fake_',        # fake_ 开头
            r'_bot$',         # _bot 结尾
            r'_fake$',        # _fake 结尾
        ]
        
        for pattern in carpet_patterns:
            if re.match(pattern, player_name, re.IGNORECASE):
                return True
                
        return False
    
    def filter_players(self, players: List[str]) -> List[str]:
        if not self.filter_enabled:
            return players
            
        filtered = []
        bots_found = []
        
        for player in players:
            if self.is_bot_player(player):
                bots_found.append(player)
            else:
                filtered.append(player)
        
        if bots_found:
            logger.info(f"过滤了 {len(bots_found)} 个假人: {', '.join(bots_found)}")
            
        return filtered


class SRVResolver:
    """SRV记录解析器"""
    
    @staticmethod
    def resolve_srv(hostname: str) -> Optional[Tuple[str, int]]:
        """解析SRV记录，返回(真实主机名, 端口)"""
        if not DNS_AVAILABLE:
            return None
            
        srv_request = "_minecraft._tcp"
        request = f"{srv_request}.{hostname}"
        
        try:
            answers = dns.resolver.resolve(request, 'SRV')
            if answers:
                answer = answers[0]
                port = answer.port
                host = str(answer.target).rstrip(".")
                logger.info(f"SRV解析成功: {hostname} -> {host}:{port}")
                return host, int(port)
        except dns.resolver.NXDOMAIN:
            logger.debug(f"SRV记录不存在: {request}")
        except dns.resolver.NoAnswer:
            logger.debug(f"SRV查询无结果: {request}")
        except dns.resolver.Timeout:
            logger.warning(f"SRV查询超时: {request}")
        except Exception as e:
            logger.warning(f"SRV解析失败: {request}, 错误: {e}")
        
        return None


class MotdQuery:
    def __init__(self, timeout: float = None):
        self.timeout = timeout or plugin_config.mc_motd_timeout
        self.player_filter = PlayerFilter()
        self.srv_resolver = SRVResolver()

    @staticmethod
    def clean_motd(motd: str) -> str:
        if not motd:
            return ""

        # 移除Minecraft颜色代码（§后跟一个字符）
        clean = re.sub(r'§[0-9a-fk-or]', '', motd)

        # 移除JSON格式的多余字符和转义字符
        clean = clean.replace('\\n', ' ').replace('\n', ' ').strip()

        # 移除多余的空格
        clean = re.sub(r'\s+', ' ', clean)

        return clean

    def parse_motd_from_description(self, description) -> str:
        if isinstance(description, str):
            return description
        elif isinstance(description, dict):
            # 处理复杂的JSON格式MOTD
            if 'text' in description:
                motd = description['text']
            elif 'extra' in description:
                # 处理包含extra字段的复杂MOTD
                motd_parts = []
                if description.get('text'):
                    motd_parts.append(description['text'])
                for extra in description['extra']:
                    if isinstance(extra, dict) and 'text' in extra:
                        motd_parts.append(extra['text'])
                    elif isinstance(extra, str):
                        motd_parts.append(extra)
                motd = ''.join(motd_parts)
            else:
                motd = str(description)
        else:
            motd = str(description)

        return motd

    async def query_server_with_direct_ping(self, host: str, port: int) -> Optional[Dict[str, Any]]:
        """使用直接ping方式查询服务器，跳过test_ping"""
        try:
            address = Address(host, port)
            pinger = ServerPinger(TCPSocketConnection(address), address=address)
            
            # 在线程池中执行阻塞操作
            loop = asyncio.get_event_loop()
            
            def _ping():
                pinger.handshake()
                return pinger.read_status()
            
            status = await asyncio.wait_for(
                loop.run_in_executor(None, _ping),
                timeout=self.timeout
            )
            
            return status
            
        except Exception as e:
            logger.debug(f"直接ping查询失败 {host}:{port}: {e}")
            return None

    async def query_server(self, ip_port: str, tag: str) -> ServerStatus:
        logger.info(f"开始查询服务器: {ip_port} ({tag})")

        # 创建基础状态对象
        status = ServerStatus(
            ip_port=ip_port,
            tag=tag,
            is_online=False
        )

        try:
            # 解析IP和端口
            if ':' in ip_port:
                host, port_str = ip_port.rsplit(':', 1)
                port = int(port_str)
            else:
                host = ip_port
                port = 25565  # 默认端口

            start_time = time.time()
            server_status = None
            method_used = ""

            # 方法1：尝试SRV记录解析
            if not server_status and DNS_AVAILABLE:
                srv_result = self.srv_resolver.resolve_srv(host)
                if srv_result:
                    srv_host, srv_port = srv_result
                    try:
                        # 先尝试直接ping方式
                        server_status = await self.query_server_with_direct_ping(srv_host, srv_port)
                        if server_status:
                            method_used = f"SRV+DirectPing({srv_host}:{srv_port})"
                        else:
                            # 如果直接ping失败，尝试常规方式
                            server = JavaServer(srv_host, srv_port)
                            loop = asyncio.get_event_loop()
                            server_status = await asyncio.wait_for(
                                loop.run_in_executor(None, server.status),
                                timeout=self.timeout
                            )
                            method_used = f"SRV+Regular({srv_host}:{srv_port})"
                    except Exception as e:
                        logger.debug(f"SRV解析后查询失败: {e}")

            # 方法2：尝试直接ping方式（针对原地址）
            if not server_status:
                server_status = await self.query_server_with_direct_ping(host, port)
                if server_status:
                    method_used = f"DirectPing({host}:{port})"

            # 方法3：常规方式查询（原地址）
            if not server_status:
                server = JavaServer(host, port)
                loop = asyncio.get_event_loop()
                server_status = await asyncio.wait_for(
                    loop.run_in_executor(None, server.status),
                    timeout=self.timeout
                )
                method_used = f"Regular({host}:{port})"

            # 如果所有方法都成功了其中一种
            if server_status:
                # 计算延迟
                status.latency = round((time.time() - start_time) * 1000, 2)
                status.is_online = True

                # 提取MOTD信息
                if hasattr(server_status, 'description'):
                    status.motd = self.parse_motd_from_description(server_status.description)
                    status.motd_clean = self.clean_motd(status.motd)

                # 提取版本信息
                if hasattr(server_status, 'version'):
                    if hasattr(server_status.version, 'name'):
                        status.version = server_status.version.name
                    if hasattr(server_status.version, 'protocol'):
                        status.protocol = server_status.version.protocol

                # 提取玩家信息
                if hasattr(server_status, 'players'):
                    status.players_online = server_status.players.online
                    status.players_max = server_status.players.max

                    # 提取玩家列表
                    if hasattr(server_status.players, 'sample') and server_status.players.sample:
                        status.players_list = [player.name for player in server_status.players.sample]
                        
                        # 过滤假人
                        status.players_list_filtered = self.player_filter.filter_players(status.players_list)
                        
                        # 如果启用了假人过滤，更新在线玩家数
                        if plugin_config.mc_motd_filter_bots and status.players_list:
                            # 计算假人数量
                            bot_count = len(status.players_list) - len(status.players_list_filtered)
                            if bot_count > 0:
                                # 估算实际在线玩家数（考虑到sample可能不完整）
                                if status.players_online and len(status.players_list) > 0:
                                    bot_ratio = bot_count / len(status.players_list)
                                    estimated_bots = int(status.players_online * bot_ratio)
                                    status.players_online = max(0, status.players_online - estimated_bots)

                # 提取服务器图标
                if hasattr(server_status, 'icon') and server_status.icon:
                    status.icon = server_status.icon

                logger.success(f"成功查询服务器: {ip_port} - 延迟: {status.latency}ms, 玩家: {status.players_online or 0}, 方法: {method_used}")

        except asyncio.TimeoutError:
            status.error_message = f"查询超时（超过{self.timeout}秒）"
            logger.warning(f"查询服务器超时: {ip_port}")

        except ConnectionRefusedError:
            status.error_message = "连接被拒绝，服务器可能离线"
            logger.warning(f"服务器连接被拒绝: {ip_port}")

        except OSError as e:
            if "Name or service not known" in str(e) or "nodename nor servname provided" in str(e):
                status.error_message = "域名解析失败"
            elif "Connection timed out" in str(e):
                status.error_message = "连接超时"
            else:
                status.error_message = f"网络错误: {str(e)}"
            logger.warning(f"网络错误查询服务器 {ip_port}: {e}")

        except ValueError as e:
            status.error_message = f"地址格式错误: {str(e)}"
            logger.error(f"地址格式错误 {ip_port}: {e}")

        except Exception as e:
            status.error_message = f"未知错误: {str(e)}"
            logger.error(f"查询服务器时发生未知错误 {ip_port}: {e}")

        return status

    async def query_all_servers(self) -> List[ServerStatus]:
        logger.info("开始查询所有服务器状态")

        try:
            # 从数据库获取所有服务器
            servers = await get_all_servers()

            if not servers:
                logger.info("数据库中没有保存的服务器")
                return []

            logger.info(f"找到 {len(servers)} 个服务器，开始并发查询")

            # 创建查询任务列表
            tasks = []
            for server in servers:
                task = self.query_server(server.ip_port, server.tag)
                tasks.append(task)

            # 并发执行所有查询
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            server_statuses = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # 处理异常情况
                    server = servers[i]
                    status = ServerStatus(
                        ip_port=server.ip_port,
                        tag=server.tag,
                        is_online=False,
                        error_message=f"查询异常: {str(result)}"
                    )
                    server_statuses.append(status)
                    logger.error(f"查询服务器 {server.ip_port} 时发生异常: {result}")
                else:
                    server_statuses.append(result)

            # 统计结果
            online_count = sum(1 for status in server_statuses if status.is_online)
            total_count = len(server_statuses)
            total_players = sum(status.players_online or 0 for status in server_statuses if status.is_online)

            logger.success(f"查询完成: {online_count}/{total_count} 个服务器在线，总玩家数: {total_players}")

            return server_statuses

        except Exception as e:
            logger.error(f"查询所有服务器时发生错误: {e}")
            return []

    async def query_server_by_ip(self, ip_port: str) -> Optional[ServerStatus]:
        try:
            # 从数据库获取服务器信息
            from .manager_ip import server_manager
            server = await server_manager.get_server_by_ip(ip_port)

            if not server:
                logger.warning(f"数据库中未找到服务器: {ip_port}")
                return None

            # 查询服务器状态
            return await self.query_server(server.ip_port, server.tag)

        except Exception as e:
            logger.error(f"查询特定服务器时发生错误: {e}")
            return None


# 创建全局查询器实例
motd_query = MotdQuery()


# 提供简单的函数接口
async def query_all_servers() -> List[ServerStatus]:
    return await motd_query.query_all_servers()


async def query_server(ip_port: str, tag: str) -> ServerStatus:
    return await motd_query.query_server(ip_port, tag)


async def query_server_by_ip(ip_port: str) -> Optional[ServerStatus]:
    return await motd_query.query_server_by_ip(ip_port)


def get_summary_stats(statuses: List[ServerStatus]) -> Dict[str, Any]:
    total = len(statuses)
    online = sum(1 for s in statuses if s.is_online)
    offline = total - online

    total_players = sum(s.players_online or 0 for s in statuses if s.is_online)
    avg_latency = None

    online_latencies = [s.latency for s in statuses if s.is_online and s.latency]
    if online_latencies:
        avg_latency = round(sum(online_latencies) / len(online_latencies), 2)

    # 计算假人统计
    total_bots_filtered = 0
    if plugin_config.mc_motd_filter_bots:
        for s in statuses:
            if s.is_online and s.players_list and s.players_list_filtered:
                total_bots_filtered += len(s.players_list) - len(s.players_list_filtered)

    return {
        "total": total,
        "online": online,
        "offline": offline,
        "total_players": total_players,
        "average_latency": avg_latency,
        "bots_filtered": total_bots_filtered,
        "filter_enabled": plugin_config.mc_motd_filter_bots
    }