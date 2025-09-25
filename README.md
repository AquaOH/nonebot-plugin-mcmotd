# Minecraft MOTD 插件

用于查询一系列 Minecraft 服务器状态并生成在一张图片上的 NoneBot 插件。

思路参考自[lgc-NB2Dev/nonebot-plugin-picmcstat: A NoneBot2 plugin generates a pic from a Minecraft server's MOTD](https://github.com/lgc-NB2Dev/nonebot-plugin-picmcstat)

## 配置

### 权限说明

管理员权限包括：

- NoneBot 超级管理员 (SUPERUSERS)
- 插件超级管理员 (MC_MOTD_SUPERUSERS)
- 群管理员或群主（需开启群管理员权限）

确保三者中有一项已经配置，否则将无法添加/删除服务器

### 配置项说明

在**配置管理员权限后**，以下项理论上均为可选配置项，默认值已经足够应对大多数场景

| 配置项                           | 类型      | 默认值                   | 作用                                                      |
| -------------------------------- | --------- | ------------------------ | --------------------------------------------------------- |
| `MC_MOTD_SUPERUSERS`             | List[str] | `[]`                     | 插件超级管理员QQ号列表                                    |
| `MC_MOTD_TIMEOUT`                | float     | `5.0`                    | 服务器查询超时时间（秒）                                  |
| `MC_MOTD_FILTER_BOTS`            | bool      | `true`                   | 是否启用假人过滤（Carpet假人）                            |
| `MC_MOTD_BOT_NAMES`              | List[str] | `["Anonymous Player"]`   | 假人名称列表                                              |
| `MC_MOTD_ALLOW_PRIVATE`          | bool      | `true`                   | 允许私聊使用插件                                          |
| `MC_MOTD_ALLOWED_GROUPS`         | List[str] | `[]`                     | 允许使用插件的群聊列表（空列表表示所有群聊都允许）        |
| `MC_MOTD_GROUP_ADMIN_PERMISSION` | bool      | `true`                   | 是否允许群管理员执行管理操作                              |
| `MC_MOTD_IMAGE_WIDTH`            | int       | `1000`                   | 图片宽度（像素）                                          |
| `MC_MOTD_ITEM_HEIGHT`            | int       | `160`                    | 每个服务器项目高度（像素）                                |
| `MC_MOTD_MARGIN`                 | int       | `30`                     | 图片边距（像素）                                          |
| `MC_MOTD_TITLE`                  | str       | `"Minecraft 服务器状态"` | 图片标题                                                  |
| `MC_MOTD_CUSTOM_FONT`            | str       | `""`                     | 自定义字体路径（相对/绝对，相对路径根目录为机器人根目录） |
| `MC_MOTD_ENABLE_COMPRESSION`     | bool      | `true`                   | 是否启用图片压缩(PNG 转 Webp)                             |
| `MC_MOTD_COMPRESSION_QUALITY`    | int       | `80`                     | 图片压缩质量（1-100 百分比）                              |

### 推荐配置

在 `.env` 文件中添加以下配置：

```env
# 权限管理
MC_MOTD_SUPERUSERS=["123456789", "987654321"]

# 可选配置
# 性能优化配置
MC_MOTD_TIMEOUT=8.0
MC_MOTD_ENABLE_COMPRESSION=true
MC_MOTD_COMPRESSION_QUALITY=75

# 权限控制配置（按需调整）
MC_MOTD_ALLOW_PRIVATE=true
MC_MOTD_GROUP_ADMIN_PERMISSION=true
MC_MOTD_ALLOWED_GROUPS=[]

# 假人过滤配置
MC_MOTD_FILTER_BOTS=true
MC_MOTD_BOT_NAMES=["Anonymous Player", "bot_", "fake_"]

# 外观定制（可选）
MC_MOTD_TITLE="我的服务器状态"
MC_MOTD_IMAGE_WIDTH=1200
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
/motd --detail
```

## 注意事项

- 必须配置管理员权限后才可使用管理功能
- 数据库文件会自动创建在插件数据目录
- 假人过滤/显示详细信息仅对支持玩家列表的服务器有效
- 建议适当调整超时时间以适应网络环境

## 图片示例

![image-20250925170806592](https://aquaoh.oss-cn-shanghai.aliyuncs.com/post/image-20250925170806592.png)