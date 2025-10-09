import re
from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import Event, MessageSegment, Message, GroupMessageEvent, PrivateMessageEvent
from nonebot.params import CommandArg
from nonebot.exception import FinishedException

from .config import plugin_config
from .permission import is_admin, is_superuser
from .scope_resolver import scope_resolver
from .manager_ip import add_server, delete_server, clear_all_servers, allocate_server_order, swap_server_order, get_all_existing_scopes
from .get_motd import query_all_servers_by_scope
from .draw_pic import draw_server_list

PERMISSION_DENIED_MSG = (
    "权限不足，仅管理员可执行管理操作。\n"
    "当前用户: {user_id}\n"
    "当前作用域: {scope_name}\n\n"
    "管理员权限包括:\n"
    "- 群管理员或群主 (需开启群管理员权限)\n"
    "- 个人列表模式下的用户本人\n\n"
    "超级管理员权限包括：\n"
    "- NoneBot 超级管理员 (SUPERUSERS)\n"
    "- 插件超级管理员 (MC_MOTD_SUPERUSERS)"
)

HELP_TEXT = (
    "🔧 Minecraft MOTD 插件使用帮助\n\n"
    "用户命令（任何人可用）：\n"
    "/motd - 查询所有服务器状态\n"
    "/motd --detail - 显示详细信息包括玩家列表\n\n"
    "/motd help - 显示此帮助信息\n\n"
    "管理员命令（超级管理员或群管理员）：\n"
    "/motd add ip:port 标签 - 添加服务器\n"
    "/motd del ip:port - 删除指定服务器\n"
    "/motd del -rf - 删除所有服务器\n"
    "/motd render allocate ip:port 位置 - 调整服务器显示顺序\n"
    "/motd render swap ip1:port ip2:port - 交换两个服务器顺序\n\n"
    "超级管理员专用命令：\n"
    "/motd scope list - 查看所有作用域列表\n"
    "/motd --scope=xxx - 查看指定作用域的服务器\n"
    "/motd --scope=all - 查看所有作用域的服务器（合并显示）\n"
    "/motd add --scope=xxx ip:port 标签 - 向指定作用域添加服务器\n"
    "/motd add --scope=all ip:port 标签 - 向所有作用域添加服务器\n"
    "/motd del --scope=xxx ip:port - 从指定作用域删除服务器\n"
    "/motd del --scope=all -rf - 删除所有作用域的所有服务器\n\n"
    "示例：\n"
    "/motd add hypixel.net Hypixel服务器\n"
    "/motd add play.example.com:25566 我的服务器\n"
    "/motd del hypixel.net\n"
    "/motd render allocate test.cn 3\n"
    "/motd render swap test.cn foobar.cn"
)

HELP_TEXT_PERSONAL = (
    "📱 个人服务器列表使用帮助\n\n"
    "你正在使用个人服务器列表模式！\n"
    "你可以添加和管理属于自己的服务器列表。\n\n"
    "可用命令：\n"
    "/motd - 查询你的服务器状态\n"
    "/motd --detail - 显示详细信息\n"
    "/motd add ip:port 标签 - 添加服务器\n"
    "/motd del ip:port - 删除服务器\n"
    "/motd del -rf - 清空所有服务器\n"
    "/motd render allocate ip:port 位置 - 调整顺序\n"
    "/motd render swap ip1:port ip2:port - 交换顺序\n\n"
    "限制：\n"
    "- 最多可添加 {limit} 个服务器{unlimited}\n\n"
    "示例：\n"
    "/motd add mc.hypixel.net Hypixel服务器\n"
    "/motd add localhost:25565 我的测试服"
)

SCOPE_DISABLED_MSG = "当前场景已禁用此功能，请联系管理员配置。"

def parse_scope_param(args_text: str) -> tuple[str, str]:
    scope_match = re.search(r'--scope=(\S+)', args_text)
    if scope_match:
        scope_value = scope_match.group(1)
        remaining_args = args_text.replace(f'--scope={scope_value}', '').strip()
        remaining_args = re.sub(r'\s+', ' ', remaining_args)
        return scope_value, remaining_args
    return None, args_text

def check_chat_permission(event: Event) -> bool:
    if plugin_config.mc_motd_multi_group_mode:
        return True
    
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
        args_text = args.extract_plain_text().strip()
        
        scope_param, remaining_args = parse_scope_param(args_text)
        
        if scope_param:
            if not is_superuser(event):
                await manage_matcher.finish("仅超级管理员可使用 --scope 参数跨作用域操作")
            target_scope = scope_param
            args_text = remaining_args
        else:
            target_scope = await scope_resolver.get_scope(event)
            if target_scope is None:
                await manage_matcher.finish(SCOPE_DISABLED_MSG)
        
        if args_text == "help" or (args_text and args_text.split()[0].lower() == "help"):
            user_id = str(event.user_id) if hasattr(event, 'user_id') else ""
            is_personal = (
                target_scope == f"private_friend_{user_id}" or 
                target_scope == f"private_temp_{user_id}"
            )
            
            if is_personal and plugin_config.mc_motd_multi_group_mode:
                limit = plugin_config.mc_motd_personal_server_limit
                unlimited_text = "" if limit > 0 else "（当前配置为不限制）"
                help_text = HELP_TEXT_PERSONAL.format(
                    limit=limit if limit > 0 else "∞",
                    unlimited=unlimited_text
                )
                await manage_matcher.finish(help_text)
            else:
                await manage_matcher.finish(HELP_TEXT)
        
        parts = args_text.split() if args_text else []
        
        if parts and parts[0].lower() == "scope" and len(parts) > 1 and parts[1].lower() == "list":
            if not is_superuser(event):
                await manage_matcher.finish("仅超级管理员可查看作用域列表")
            await handle_scope_list()
            return
        
        if not plugin_config.mc_motd_multi_group_mode:
            if not check_chat_permission(event):
                return
        
        if not args_text or args_text == "--detail":
            show_detail = args_text == "--detail"
            await handle_query_logic(event, target_scope, show_detail)
            return
        
        if not parts:
            await handle_query_logic(event, target_scope, False)
            return
        
        action = parts[0].lower()
        
        if action == "render" and len(parts) > 1:
            if scope_param and not is_superuser(event):
                await manage_matcher.finish("仅超级管理员可跨作用域操作")
            if not scope_param and not is_admin(event, target_scope):
                scope_name = scope_resolver.get_scope_display_name(target_scope)
                await manage_matcher.finish(PERMISSION_DENIED_MSG.format(user_id=event.user_id, scope_name=scope_name))
            
            render_action = parts[1].lower()
            if render_action == "allocate":
                await handle_allocate_order(parts[2:], target_scope)
            elif render_action == "swap":
                await handle_swap_order(parts[2:], target_scope)
            else:
                await manage_matcher.finish(f"未知渲染命令: {render_action}\n使用 /motd help 查看帮助。")
            return
        
        if scope_param and not is_superuser(event):
            await manage_matcher.finish("仅超级管理员可跨作用域操作")
        
        if not scope_param and not is_admin(event, target_scope):
            scope_name = scope_resolver.get_scope_display_name(target_scope)
            await manage_matcher.finish(PERMISSION_DENIED_MSG.format(user_id=event.user_id, scope_name=scope_name))
        
        if action == "add":
            await handle_add_server(parts, target_scope, scope_param == "all")
        elif action == "del":
            await handle_delete_server(parts, target_scope, scope_param == "all")
        else:
            await manage_matcher.finish(f"未知命令: {action}\n使用 /motd help 查看帮助。")

    except FinishedException:
        pass
    except Exception as e:
        logger.error(f"处理管理命令时发生错误: {e}")

async def handle_scope_list():
    scopes = await get_all_existing_scopes()
    
    if not scopes:
        await manage_matcher.finish("当前没有任何作用域存在服务器")
    
    scope_info = []
    for scope in sorted(scopes):
        display_name = scope_resolver.get_scope_display_name(scope)
        scope_info.append(f"- {scope} ({display_name})")
    
    message = "📋 所有作用域列表：\n\n" + "\n".join(scope_info)
    await manage_matcher.finish(message)

async def handle_add_server(parts, scope: str, scope_all: bool):
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
    
    if scope_all:
        scopes = await get_all_existing_scopes()
        if not scopes:
            await manage_matcher.finish("没有找到任何作用域")
        
        results = []
        for s in scopes:
            success, message = await add_server(ip_port, tag, s)
            results.append(f"{scope_resolver.get_scope_display_name(s)}: {'✅' if success else '❌'} {message}")
        
        await manage_matcher.finish("批量添加结果：\n" + "\n".join(results))
    else:
        success, message = await add_server(ip_port, tag, scope)
        
        if success:
            scope_name = scope_resolver.get_scope_display_name(scope)
            logger.info(f"管理员添加了服务器: {ip_port} - {tag} (scope: {scope})")
            await manage_matcher.finish(f"✅ 已添加服务器: {tag}\n作用域: {scope_name}")
        else:
            await manage_matcher.finish(f"❌ {message}")

async def handle_delete_server(parts, scope: str, scope_all: bool):
    if len(parts) < 2:
        await manage_matcher.finish(
            "格式错误。正确格式：\n"
            "/motd del ip:port - 删除指定服务器\n"
            "/motd del -rf - 删除所有服务器"
        )
    
    if parts[1] == "-rf":
        if scope_all:
            scopes = await get_all_existing_scopes()
            if not scopes:
                await manage_matcher.finish("没有找到任何作用域")
            
            results = []
            for s in scopes:
                success, message = await clear_all_servers(s)
                results.append(f"{scope_resolver.get_scope_display_name(s)}: {'✅' if success else '❌'}")
            
            logger.warning("超级管理员清空了所有作用域的服务器")
            await manage_matcher.finish("批量清空结果：\n" + "\n".join(results))
        else:
            success, message = await clear_all_servers(scope)
            if success:
                logger.warning(f"管理员清空了作用域 {scope} 的所有服务器")
                await manage_matcher.finish("✅ 已清空所有服务器")
            else:
                await manage_matcher.finish(f"❌ {message}")
    else:
        ip_port = parts[1]
        
        if scope_all:
            scopes = await get_all_existing_scopes()
            if not scopes:
                await manage_matcher.finish("没有找到任何作用域")
            
            results = []
            for s in scopes:
                success, message = await delete_server(ip_port, s)
                results.append(f"{scope_resolver.get_scope_display_name(s)}: {'✅' if success else '❌'}")
            
            await manage_matcher.finish("批量删除结果：\n" + "\n".join(results))
        else:
            success, message = await delete_server(ip_port, scope)
            if success:
                logger.warning(f"管理员删除了服务器: {ip_port} (scope: {scope})")
                await manage_matcher.finish("✅ 已删除服务器")
            else:
                await manage_matcher.finish(f"❌ {message}")

async def handle_allocate_order(parts, scope: str):
    if len(parts) < 2:
        await manage_matcher.finish("格式错误。正确格式：/motd render allocate ip:port 位置")
    
    ip_port = parts[0]
    try:
        target_position = int(parts[1])
    except ValueError:
        await manage_matcher.finish("位置必须是数字")
    
    success, message = await allocate_server_order(ip_port, target_position, scope)
    if success:
        logger.info(f"管理员调整服务器顺序: {ip_port} -> 位置 {target_position} (scope: {scope})")
        await manage_matcher.finish(f"✅ {message}")
    else:
        await manage_matcher.finish(f"❌ {message}")

async def handle_swap_order(parts, scope: str):
    if len(parts) < 2:
        await manage_matcher.finish("格式错误。正确格式：/motd render swap ip1:port ip2:port")
    
    ip_port_a = parts[0]
    ip_port_b = parts[1]
    
    success, message = await swap_server_order(ip_port_a, ip_port_b, scope)
    if success:
        logger.info(f"管理员交换服务器顺序: {ip_port_a} <-> {ip_port_b} (scope: {scope})")
        await manage_matcher.finish(f"✅ {message}")
    else:
        await manage_matcher.finish(f"❌ {message}")

async def handle_query_logic(event: Event, scope: str, show_detail: bool):
    user_desc = f"用户 {event.user_id}"
    if isinstance(event, GroupMessageEvent):
        user_desc = f"群 {event.group_id} 的用户 {event.user_id}"
    elif isinstance(event, PrivateMessageEvent):
        user_desc = f"私聊用户 {event.user_id} ({event.sub_type})"
    
    scope_name = scope_resolver.get_scope_display_name(scope)
    logger.info(f"{user_desc} 请求查询服务器状态{'（详细模式）' if show_detail else ''} - 作用域: {scope_name}")

    await manage_matcher.send("正在查询服务器状态，请稍候...")
    
    if scope == "all":
        all_scopes = await get_all_existing_scopes()
        if not all_scopes:
            await manage_matcher.finish("当前没有任何作用域存在服务器")
        
        all_statuses = []
        for s in all_scopes:
            statuses = await query_all_servers_by_scope(s)
            all_statuses.extend(statuses)
        
        server_statuses = all_statuses
    else:
        server_statuses = await query_all_servers_by_scope(scope)
    
    if not server_statuses:
        await manage_matcher.finish(
            f"还没有添加任何服务器。\n"
            f"当前作用域: {scope_name}\n"
            f"管理员可以使用 /motd add ip:port 标签 来添加服务器。"
        )

    image_bytes = await draw_server_list(server_statuses, show_detail=show_detail, scope=scope)
    
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