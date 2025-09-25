import re
from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import Event, MessageSegment, Message, GroupMessageEvent, PrivateMessageEvent
from nonebot.params import CommandArg
from nonebot.exception import FinishedException

from .config import plugin_config
from .permission import is_admin
from .manager_ip import add_server, delete_server, clear_all_servers
from .get_motd import query_all_servers
from .draw_pic import draw_server_list

PERMISSION_DENIED_MSG = (
    "权限不足，仅管理员可执行管理操作。\n"
    "当前用户: {user_id}\n"
    "管理员权限包括：\n"
    "- NoneBot 超级管理员 (SUPERUSERS)\n"
    "- 插件超级管理员 (MC_MOTD_SUPERUSERS)\n"
    "- 群管理员或群主 (需开启群管理员权限)"
)

HELP_TEXT = (
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

def check_chat_permission(event: Event) -> bool:
    if isinstance(event, PrivateMessageEvent):
        return plugin_config.mc_motd_allow_private
    elif isinstance(event, GroupMessageEvent):
        if not plugin_config.mc_motd_allowed_groups:
            return True
        return str(event.group_id) in plugin_config.mc_motd_allowed_groups
    return False

manage_matcher = on_command("motd", priority=10, block=True)

@manage_matcher.handle()
async def handle_manage(event: Event, args: Message = CommandArg()):
    try:
        if not check_chat_permission(event):
            return

        args_text = args.extract_plain_text().strip()
        
        if not args_text:
            await handle_query_logic(event, False)
            return
        
        if args_text == "--detail":
            await handle_query_logic(event, True)
            return
        
        parts = args_text.split()
        if not parts:
            await handle_query_logic(event, False)
            return
        
        action = parts[0].lower()
        
        if action == "help":
            await manage_matcher.finish(HELP_TEXT)
        
        if not is_admin(event):
            await manage_matcher.finish(PERMISSION_DENIED_MSG.format(user_id=event.user_id))
        
        if action == "add":
            await handle_add_server(parts)
        elif action == "del":
            await handle_delete_server(parts)
        else:
            await manage_matcher.finish(f"未知命令: {action}\n使用 /motd help 查看帮助。")

    except FinishedException:
        pass
    except Exception as e:
        logger.error(f"处理管理命令时发生错误: {e}")

async def handle_add_server(parts):
    if len(parts) < 3:
        await manage_matcher.finish("格式错误。正确格式：/motd add ip:port 服务器标签")
    
    ip_port = parts[1]
    tag = " ".join(parts[2:])
    
    if not re.match(r'^[a-zA-Z0-9\.\-_]+(?::\d{1,5})?$', ip_port):
        await manage_matcher.finish("IP地址格式错误。格式：ip:port 或 域名:port")
    
    if ':' in ip_port:
        try:
            port = int(ip_port.split(':')[-1])
            if not (1 <= port <= 65535):
                await manage_matcher.finish("端口号必须在 1-65535 范围内")
        except ValueError:
            await manage_matcher.finish("端口号必须是数字")
    
    success, message = await add_server(ip_port, tag)
    if success:
        logger.info(f"管理员添加了服务器: {ip_port} - {tag}")
        await manage_matcher.finish(f"✅ 已添加服务器: {tag}")
    else:
        await manage_matcher.finish("❌ 添加失败")

async def handle_delete_server(parts):
    if len(parts) < 2:
        await manage_matcher.finish("格式错误。正确格式：\n/motd del ip:port - 删除指定服务器\n/motd del -rf - 删除所有服务器")
    
    if parts[1] == "-rf":
        success, message = await clear_all_servers()
        result_msg = "✅ 已清空所有服务器" if success else "❌ 清空失败"
        if success:
            logger.warning("管理员清空了所有服务器")
        await manage_matcher.finish(result_msg)
    else:
        ip_port = parts[1]
        success, message = await delete_server(ip_port)
        result_msg = "✅ 已删除服务器" if success else "❌ 删除失败"
        if success:
            logger.warning(f"管理员删除了服务器: {ip_port}")
        await manage_matcher.finish(result_msg)

async def handle_query_logic(event: Event, show_detail: bool):
    try:
        logger.info(f"用户 {event.user_id} 请求查询服务器状态{'（详细模式）' if show_detail else ''}")

        await manage_matcher.send("正在查询服务器状态，请稍候...")
        
        server_statuses = await query_all_servers()
        
        if not server_statuses:
            await manage_matcher.finish("还没有添加任何服务器。\n管理员可以使用 /motd add ip:port 标签 来添加服务器。")

        image_bytes = await draw_server_list(server_statuses, show_detail=show_detail)
        
        if image_bytes:
            image_msg = MessageSegment.image(image_bytes)
            
            if plugin_config.mc_motd_filter_bots:
                bot_filtered_servers = []
                for status in server_statuses:
                    if status.is_online and status.players_list and status.players_list_filtered:
                        bot_count = len(status.players_list) - len(status.players_list_filtered)
                        if bot_count > 0:
                            bot_filtered_servers.append(f"{status.tag}过滤了{bot_count}个假人")
                
                if bot_filtered_servers:
                    bot_message = "\n".join(bot_filtered_servers)
                    await manage_matcher.finish([image_msg, MessageSegment.text("\n" + bot_message)])
                else:
                    await manage_matcher.finish(image_msg)
            else:
                await manage_matcher.finish(image_msg)
        else:
            logger.error("图片生成失败")
            await manage_matcher.finish("图片生成错误，请向管理员询问")

    except FinishedException:
        pass
    except Exception as e:
        logger.error(f"查询服务器状态时发生错误: {e}")
        await manage_matcher.finish("查询服务器状态时发生错误，请向管理员询问")