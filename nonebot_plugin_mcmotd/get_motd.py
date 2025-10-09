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
    ip_port: str
    tag: str
    is_online: bool
    motd: Optional[str] = None
    motd_clean: Optional[str] = None
    icon: Optional[str] = None
    version: Optional[str] = None
    protocol: Optional[int] = None
    players_online: Optional[int] = None
    players_max: Optional[int] = None
    players_list: Optional[List[str]] = field(default_factory=list)
    players_list_filtered: Optional[List[str]] = field(default_factory=list)
    latency: Optional[float] = None
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
        self.bot_patterns = plugin_config.mc_motd_bot_patterns
        
    def is_bot_player(self, player_name: str) -> bool:
        if not self.filter_enabled:
            return False
            
        if player_name in self.bot_names:
            return True
        
        if not self.bot_patterns:
            return False
        
        for pattern in self.bot_patterns:
            try:
                if re.match(pattern, player_name, re.IGNORECASE):
                    return True
            except re.error as e:
                logger.warning(f"正则表达式错误: {pattern}, 错误: {e}")
                continue
                
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
    @staticmethod
    def resolve_srv(hostname: str) -> Optional[Tuple[str, int]]:
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

        clean = re.sub(r'§[0-9a-fk-or]', '', motd)
        clean = clean.replace('\\n', ' ').replace('\n', ' ').strip()
        clean = re.sub(r'\s+', ' ', clean)

        return clean

    def parse_motd_from_description(self, description) -> str:
        if isinstance(description, str):
            return description
        elif isinstance(description, dict):
            if 'text' in description:
                motd = description['text']
            elif 'extra' in description:
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
        try:
            address = Address(host, port)
            pinger = ServerPinger(TCPSocketConnection(address), address=address)
            
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

        status = ServerStatus(
            ip_port=ip_port,
            tag=tag,
            is_online=False
        )

        try:
            if ':' in ip_port:
                host, port_str = ip_port.rsplit(':', 1)
                port = int(port_str)
            else:
                host = ip_port
                port = 25565

            start_time = time.time()
            server_status = None
            method_used = ""

            if not server_status and DNS_AVAILABLE:
                srv_result = self.srv_resolver.resolve_srv(host)
                if srv_result:
                    srv_host, srv_port = srv_result
                    try:
                        server_status = await self.query_server_with_direct_ping(srv_host, srv_port)
                        if server_status:
                            method_used = f"SRV+DirectPing({srv_host}:{srv_port})"
                        else:
                            server = JavaServer(srv_host, srv_port)
                            loop = asyncio.get_event_loop()
                            server_status = await asyncio.wait_for(
                                loop.run_in_executor(None, server.status),
                                timeout=self.timeout
                            )
                            method_used = f"SRV+Regular({srv_host}:{srv_port})"
                    except Exception as e:
                        logger.debug(f"SRV解析后查询失败: {e}")

            if not server_status:
                server_status = await self.query_server_with_direct_ping(host, port)
                if server_status:
                    method_used = f"DirectPing({host}:{port})"

            if not server_status:
                server = JavaServer(host, port)
                loop = asyncio.get_event_loop()
                server_status = await asyncio.wait_for(
                    loop.run_in_executor(None, server.status),
                    timeout=self.timeout
                )
                method_used = f"Regular({host}:{port})"

            if server_status:
                status.latency = round((time.time() - start_time) * 1000, 2)
                status.is_online = True

                if hasattr(server_status, 'description'):
                    status.motd = self.parse_motd_from_description(server_status.description)
                    status.motd_clean = self.clean_motd(status.motd)

                if hasattr(server_status, 'version'):
                    if hasattr(server_status.version, 'name'):
                        status.version = server_status.version.name
                    if hasattr(server_status.version, 'protocol'):
                        status.protocol = server_status.version.protocol

                if hasattr(server_status, 'players'):
                    status.players_online = server_status.players.online
                    status.players_max = server_status.players.max

                    if hasattr(server_status.players, 'sample') and server_status.players.sample:
                        status.players_list = [player.name for player in server_status.players.sample]
                        status.players_list_filtered = self.player_filter.filter_players(status.players_list)
                        
                        if plugin_config.mc_motd_filter_bots and status.players_list:
                            bot_count = len(status.players_list) - len(status.players_list_filtered)
                            if bot_count > 0:
                                if status.players_online and len(status.players_list) > 0:
                                    bot_ratio = bot_count / len(status.players_list)
                                    estimated_bots = int(status.players_online * bot_ratio)
                                    status.players_online = max(0, status.players_online - estimated_bots)

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
            servers = await get_all_servers()

            if not servers:
                logger.info("数据库中没有保存的服务器")
                return []

            logger.info(f"找到 {len(servers)} 个服务器，开始并发查询")

            tasks = []
            for server in servers:
                task = self.query_server(server.ip_port, server.tag)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            server_statuses = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
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
            from .manager_ip import server_manager
            server = await server_manager.get_server_by_ip(ip_port)

            if not server:
                logger.warning(f"数据库中未找到服务器: {ip_port}")
                return None

            return await self.query_server(server.ip_port, server.tag)

        except Exception as e:
            logger.error(f"查询特定服务器时发生错误: {e}")
            return None

motd_query = MotdQuery()

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

async def query_all_servers_by_scope(scope: str = "global") -> List[ServerStatus]:
    logger.info(f"开始查询作用域 {scope} 的服务器状态")

    try:
        from .manager_ip import get_all_servers
        servers = await get_all_servers(scope)

        if not servers:
            logger.info(f"作用域 {scope} 中没有保存的服务器")
            return []

        logger.info(f"在作用域 {scope} 中找到 {len(servers)} 个服务器，开始并发查询")

        tasks = []
        for server in servers:
            task = motd_query.query_server(server.ip_port, server.tag)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        server_statuses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
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

        online_count = sum(1 for status in server_statuses if status.is_online)
        total_count = len(server_statuses)
        total_players = sum(status.players_online or 0 for status in server_statuses if status.is_online)

        logger.success(f"作用域 {scope} 查询完成: {online_count}/{total_count} 个服务器在线，总玩家数: {total_players}")

        return server_statuses

    except Exception as e:
        logger.error(f"查询作用域 {scope} 的服务器时发生错误: {e}")
        return []