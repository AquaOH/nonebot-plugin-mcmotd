import re
from typing import List, Optional
from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment, Message, GroupMessageEvent, PrivateMessageEvent
from nonebot.params import CommandArg
from nonebot.exception import FinishedException

from .config import plugin_config
from .permission import is_admin
from .manager_ip import add_server, delete_server, clear_all_servers
from .get_motd import query_all_servers
from .draw_pic import draw_server_list

def check_chat_permission(event: Event) -> bool:
    """检查是否允许在当前会话中响应"""
    if isinstance(event, PrivateMessageEvent):
        return plugin_config.mc_motd_allow_private
    elif isinstance(event, GroupMessageEvent):
        # 如果允许的群聊列表为空，则所有群聊都允许
        if not plugin_config.mc_motd_allowed_groups:
            return True
        return str(event.group_id) in plugin_config.mc_motd_allowed_groups
    return False

# 管理命令 - 支持查询和管理功能
manage_matcher = on_command("motd", priority=10, block=True)


@manage_matcher.handle()
async def handle_manage(event: Event, args: Message = CommandArg()):
    try:
        # 检查会话权限
        if not check_chat_permission(event):
            return  # 静默忽略，不响应

        # 解析命令参数
        args_text = args.extract_plain_text().strip()
        
        # 如果没有参数，则进行查询
        if not args_text:
            await handle_query_logic(event, False)
            return
        
        # 检查是否为--detail参数
        if args_text == "--detail":
            await handle_query_logic(event, True)
            return
        
        # 分割参数
        parts = args_text.split()
        if not parts:
            await handle_query_logic(event, False)
            return
        
        action = parts[0].lower()
        
        # 帮助命令 - 所有人可用
        if action == "help":
            help_text = (
                "🔧 Minecraft MOTD 插件使用帮助\n\n"
                "用户命令（任何人可用）：\n"
                "/motd - 查询所有服务器状态\n"
                "/motd --detail - 显示详细信息包括玩家列表\n\n"
                "管理员命令（超级管理员或群管理员）：\n"
                "/motd add ip:port 标签 - 添加服务器\n"
                "/motd del ip:port - 删除指定服务器\n"
                "/motd del -rf - 删除所有服务器\n"
                "/motd help - 显示此帮助信息\n\n"
                "示例：\n"
                "/motd add hypixel.net Hypixel服务器\n"
                "/motd add play.example.com:25566 我的服务器\n"
                "/motd del hypixel.net"
            )
            await manage_matcher.finish(help_text)
        
        # 检查管理员权限
        if not is_admin(event):
            await manage_matcher.finish(
                f"权限不足，仅管理员可执行管理操作。\n"
                f"当前用户: {event.user_id}\n"
                f"管理员权限包括：\n"
                f"- NoneBot 超级管理员 (SUPERUSERS)\n"
                f"- 插件超级管理员 (MC_MOTD_SUPERUSERS)\n"
                f"- 群管理员或群主 (需开启群管理员权限)"
            )
        
        # 添加服务器
        if action == "add":
            if len(parts) < 3:
                await manage_matcher.finish("格式错误。正确格式：/motd add ip:port 服务器标签")
            
            ip_port = parts[1]
            tag = " ".join(parts[2:])  # 标签可能包含空格
            
            # 验证IP地址格式
            if not re.match(r'^[a-zA-Z0-9\.\-_]+(?::\d{1,5})?$', ip_port):
                await manage_matcher.finish("IP地址格式错误。格式：ip:port 或 域名:port")
            
            # 验证端口范围
            if ':' in ip_port:
                try:
                    port = int(ip_port.split(':')[-1])
                    if not (1 <= port <= 65535):
                        await manage_matcher.finish("端口号必须在 1-65535 范围内")
                except ValueError:
                    await manage_matcher.finish("端口号必须是数字")
            
            # 添加服务器
            success, message = await add_server(ip_port, tag)
            if success:
                logger.info(f"管理员 {event.user_id} 添加了服务器: {ip_port} - {tag}")
                await manage_matcher.finish(f"✅ 已添加服务器: {tag}")
            else:
                await manage_matcher.finish(f"❌ 添加失败")
        
        # 删除服务器
        elif action == "del":
            if len(parts) < 2:
                await manage_matcher.finish("格式错误。正确格式：\n/motd del ip:port - 删除指定服务器\n/motd del -rf - 删除所有服务器")
            
            if parts[1] == "-rf":
                # 删除所有服务器 - 直接执行，无需确认
                success, message = await clear_all_servers()
                if success:
                    logger.warning(f"管理员 {event.user_id} 清空了所有服务器")
                    await manage_matcher.finish("✅ 已清空所有服务器")
                else:
                    await manage_matcher.finish("❌ 清空失败")
            else:
                ip_port = parts[1]
                success, message = await delete_server(ip_port)
                if success:
                    logger.warning(f"管理员 {event.user_id} 删除了服务器: {ip_port}")
                    await manage_matcher.finish("✅ 已删除服务器")
                else:
                    await manage_matcher.finish("❌ 删除失败")
        
        else:
            await manage_matcher.finish(f"未知命令: {action}\n使用 /motd help 查看帮助。")

    except FinishedException:
        # 静默处理，不向用户发送错误信息
        pass
    except Exception as e:
        logger.error(f"处理管理命令时发生错误: {e}")
        # 不向用户发送错误信息，静默处理


async def handle_query_logic(event: Event, show_detail: bool):
    """查询逻辑的公共函数"""
    try:
        logger.info(f"用户 {event.user_id} 请求查询服务器状态{'（详细模式）' if show_detail else ''}")

        # 查询所有服务器状态
        await manage_matcher.send("正在查询服务器状态，请稍候...")
        
        server_statuses = await query_all_servers()
        
        if not server_statuses:
            await manage_matcher.finish("还没有添加任何服务器。\n管理员可以使用 /motd add ip:port 标签 来添加服务器。")

        # 生成状态图片
        image_bytes = await draw_server_list(server_statuses, show_detail=show_detail)
        
        if image_bytes:
            # 发送图片
            image_msg = MessageSegment.image(image_bytes)
            
            # 检查是否有假人过滤信息需要显示
            if plugin_config.mc_motd_filter_bots:
                bot_filtered_servers = []
                for status in server_statuses:
                    if status.is_online and status.players_list and status.players_list_filtered:
                        bot_count = len(status.players_list) - len(status.players_list_filtered)
                        if bot_count > 0:
                            bot_filtered_servers.append(f"{status.tag}过滤了{bot_count}个假人")
                
                if bot_filtered_servers:
                    # 如果有假人过滤信息，一起发送
                    bot_message = "\n".join(bot_filtered_servers)
                    await manage_matcher.finish([image_msg, MessageSegment.text("\n" + bot_message)])
                else:
                    # 没有假人过滤信息，只发送图片
                    await manage_matcher.finish(image_msg)
            else:
                # 未启用假人过滤，只发送图片
                await manage_matcher.finish(image_msg)
        else:
            # 如果图片生成失败，显示错误信息
            logger.error("图片生成失败")
            await manage_matcher.finish("图片生成错误，请向管理员询问")

    except FinishedException:
        pass
    except Exception as e:
        logger.error(f"查询服务器状态时发生错误: {e}")
        await manage_matcher.finish("查询服务器状态时发生错误，请向管理员询问")