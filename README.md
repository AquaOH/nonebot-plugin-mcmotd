# Minecraft MOTD 插件

用于查询一系列 Minecraft 服务器状态并生成在一张图片上的 NoneBot 插件。

思路参考自[lgc-NB2Dev/nonebot-plugin-picmcstat: A NoneBot2 plugin generates a pic from a Minecraft server's MOTD](https://github.com/lgc-NB2Dev/nonebot-plugin-picmcstat)

## 配置

在 `.env` 文件中添加以下配置：

### 必需配置

```env
# 超级管理员QQ号列表（必须配置）
MC_MOTD_SUPERUSERS=["123456789", "987654321"]
```

### 可选配置

```env
# 允许私聊使用插件
MC_MOTD_ALLOW_PRIVATE=true

# 允许使用插件的群聊列表（空列表表示所有群聊都允许）
MC_MOTD_ALLOWED_GROUPS=["123456789"]

# 查询超时时间（秒）
MC_MOTD_TIMEOUT=5.0

# 是否启用假人过滤（Carpet假人）
MC_MOTD_FILTER_BOTS=true

# 假人名称列表
MC_MOTD_BOT_NAMES=["Anonymous Player"]

# 图片配置
MC_MOTD_IMAGE_WIDTH=1000
MC_MOTD_ITEM_HEIGHT=160
MC_MOTD_MARGIN=30
MC_MOTD_TITLE="Minecraft 服务器状态"

# 数据库路径
MC_MOTD_DB_PATH="data/minecraft_servers.db"

# 自定义字体设置（字体文件需放在 data/fonts/ 目录下）
# 只需填写字体文件名，不含扩展名
# 例如：字体文件为 MyFont.ttf，则配置为 MC_MOTD_CUSTOM_FONT=MyFont
MC_MOTD_CUSTOM_FONT=MyFont
```

## 使用

### 用户命令

- `/motd` - 查询所有服务器状态
- `/motd --detail` - 显示详细信息包括玩家列表

### 管理员命令

- `/motd add ip:port 标签` - 添加服务器
- `/motd del ip:port` - 删除服务器
- `/motd del -rf` - 删除所有服务器
- `/motd help` - 显示帮助

### 示例

```
/motd add hypixel.net Hypixel服务器
/motd add play.example.com:25566 我的服务器
/motd del hypixel.net
```

## 注意事项

- 必须配置超级管理员才能使用管理功能
- 数据库文件会自动创建
- 假人过滤仅对支持玩家列表的服务器有效