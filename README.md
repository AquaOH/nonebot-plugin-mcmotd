# Minecraft MOTD 插件

用于查询一系列 Minecraft 服务器状态并生成在一张图片上的 NoneBot 插件。支持多群聊隔离、私聊策略配置等高级功能。

思路参考自 [lgc-NB2Dev/nonebot-plugin-picmcstat](https://github.com/lgc-NB2Dev/nonebot-plugin-picmcstat)

## 工作模式

插件支持两种工作模式，可通过 `MC_MOTD_MULTI_GROUP_MODE` 配置项切换：

```mermaid
graph TD
    A[插件启动] --> B{MC_MOTD_MULTI_GROUP_MODE}
    B -->|false| C[传统模式]
    B -->|true| D[多群聊隔离模式]
    
    C --> C1[全局共享服务器列表]
    C --> C2[所有群聊使用相同列表]
    C --> C3[简单权限管理]
    
    D --> D1[独立服务器列表]
    D --> D2[群聊隔离]
    D --> D3[群组共享]
    D --> D4[个人列表]
    D --> D5[动态策略]
```

### 传统模式（默认）

所有群聊和私聊共享同一个全局服务器列表，适合简单场景。

### 多群聊隔离模式

不同群聊、私聊可以拥有独立的服务器列表，支持：

- **群聊隔离**：每个群独立的服务器列表
- **群组共享**：多个群共享同一服务器列表
- **个人列表**：用户在私聊中拥有独立列表（可自己管理）
- **动态策略**：群临时会话可跟随来源群

## 权限说明

权限管理根据工作模式有所不同：

```mermaid
graph TD
    A[用户类型] -->|管理所有作用域| B[超级管理员]
    A -->|管理特定作用域| C[QQ群管理员/群主]
    A --> D[普通用户]
    
    B --> B1[NoneBot 超级管理员<br/>SUPERUSERS]
    B --> B2[插件超级管理员<br/>MC_MOTD_SUPERUSERS]

    

    C --> C2{MC_MOTD_GROUP_ADMIN_PERMISSION}
    C2 -->|true| C3[管理本群服务器列表]
    C2 -->|false| C4[无管理权限]
    
    D --> D1{模式判断}
    D1 -->|传统模式| D2[无管理权限]
    D1 -->|多群聊模式<br/>personal策略| D3[管理个人列表]
```

### 传统模式权限

管理员权限包括：

- NoneBot 超级管理员 (SUPERUSERS)
- 插件超级管理员 (MC_MOTD_SUPERUSERS)
- 群管理员或群主（需开启群管理员权限）

### 多群聊隔离模式权限

权限规则：

- **超级管理员**：管理所有作用域的服务器
- **群管理员**：只能管理所在群的服务器列表
- **普通用户**：在 personal 模式下可管理自己的个人列表

## 配置项说明

### 基础配置

| 配置项                           | 类型      | 默认值                                                       | 作用                                                         |
| -------------------------------- | --------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| `MC_MOTD_SUPERUSERS`             | List[str] | `[]`                                                         | 插件超级管理员QQ号列表                                       |
| `MC_MOTD_TIMEOUT`                | float     | `5.0`                                                        | 服务器查询超时时间（秒）                                     |
| `MC_MOTD_FILTER_BOTS`            | bool      | `true`                                                       | 是否启用假人过滤                                             |
| `MC_MOTD_BOT_NAMES`              | List[str] | `["Anonymous Player"]`                                       | 假人名称列表（精确匹配）                                     |
| `MC_MOTD_BOT_PATTERNS`           | List[str] | `["^player_\\d+$", "^bot_\\d+$", "^fake_\\d+$", "^\\[Bot\\]", "^\\[Fake\\]"]` | 假人正则表达式列表（设为 `[]` 则不使用正则匹配）             |
| `MC_MOTD_ALLOW_PRIVATE`          | bool      | `true`                                                       | 允许私聊使用插件（仅传统模式有效）                           |
| `MC_MOTD_ALLOWED_GROUPS`         | List[str] | `[]`                                                         | 允许使用插件的群聊列表（空列表表示所有群聊都允许，仅传统模式有效） |
| `MC_MOTD_GROUP_ADMIN_PERMISSION` | bool      | `true`                                                       | 是否允许群管理员执行管理操作                                 |

### 多群聊隔离配置

| 配置项                                | 类型            | 默认值           | 作用                                                         |
| ------------------------------------- | --------------- | ---------------- | ------------------------------------------------------------ |
| `MC_MOTD_MULTI_GROUP_MODE`            | bool            | `false`          | 是否启用多群聊隔离模式                                       |
| `MC_MOTD_GROUP_CLUSTERS`              | Dict[str, List] | `{}`             | 群聊分组配置，同组群共享服务器列表<br />格式：`{"组名": ["群号1", "群号2"]}`<br />留空则每个群都是独立的作用域，各群的服务器列表互不影响。 |
| `MC_MOTD_PRIVATE_FRIEND_STRATEGY`     | str             | `"personal"`     | 好友私聊策略：`disabled`/`global`/`personal`                 |
| `MC_MOTD_PRIVATE_GROUP_TEMP_STRATEGY` | str             | `"follow_group"` | 群临时会话策略：`disabled`/`global`/`personal`/`follow_group` |
| `MC_MOTD_TRACK_USER_ACTIVITY`         | bool            | `true`           | 是否追踪用户活跃群（用于 follow_group 策略）                 |
| `MC_MOTD_FOLLOW_GROUP_FALLBACK`       | str             | `"personal"`     | follow_group 无法确定来源群时的降级策略：`personal`/`global` |
| `MC_MOTD_PERSONAL_SERVER_LIMIT`       | int             | `10`             | personal 模式下用户可添加的服务器数量上限（0 表示不限制）    |

#### 私聊策略决策流程

```mermaid
flowchart TD
    A[用户私聊] --> B{消息类型}
    B -->|好友私聊| C{PRIVATE_FRIEND_STRATEGY}
    B -->|群临时会话| D{PRIVATE_GROUP_TEMP_STRATEGY}
    
    C -->|disabled| E1[功能禁用]
    C -->|global| E2[使用全局列表]
    C -->|personal| E3[使用个人列表]
    
    D -->|disabled| F1[功能禁用]
    D -->|global| F2[使用全局列表]
    D -->|personal| F3[使用个人列表]
    D -->|follow_group| G{能否确定来源群?}
    
    G -->|是| H[使用来源群列表]
    G -->|否| I{FOLLOW_GROUP_FALLBACK}
    I -->|personal| J[降级到个人列表]
    I -->|global| K[降级到全局列表]
```

### 图片渲染配置

| 配置项                        | 类型 | 默认值                   | 作用                                                      |
| ----------------------------- | ---- | ------------------------ | --------------------------------------------------------- |
| `MC_MOTD_IMAGE_WIDTH`         | int  | `1000`                   | 图片宽度（像素）                                          |
| `MC_MOTD_ITEM_HEIGHT`         | int  | `160`                    | 每个服务器项目高度（像素）                                |
| `MC_MOTD_MARGIN`              | int  | `30`                     | 图片边距（像素）                                          |
| `MC_MOTD_TITLE`               | str  | `"Minecraft 服务器状态"` | 图片标题                                                  |
| `MC_MOTD_CUSTOM_FONT`         | str  | `""`                     | 自定义字体路径（相对/绝对，相对路径根目录为机器人根目录） |
| `MC_MOTD_ENABLE_COMPRESSION`  | bool | `false`                  | 是否启用图片压缩(PNG 转 WebP)                             |
| `MC_MOTD_COMPRESSION_QUALITY` | int  | `80`                     | 图片压缩质量（1-100 百分比）                              |

### 配置示例

#### 传统模式（默认）

```env
# 权限管理
MC_MOTD_SUPERUSERS=["123456789", "987654321"]

# 权限控制
MC_MOTD_ALLOW_PRIVATE=true
MC_MOTD_GROUP_ADMIN_PERMISSION=true
MC_MOTD_ALLOWED_GROUPS=["114514"] # 遗留配置，实现在传统模式下实现简单的过滤群聊
```

#### 多群聊隔离模式 - 完全隔离

```env
# 启用多群聊模式
MC_MOTD_MULTI_GROUP_MODE=true

# 群A和群B共享服务器列表
MC_MOTD_GROUP_CLUSTERS='{"cluster_a": ["123456789", "987654321"]}' # 虽然组名可以自定义，但是我推荐你使用cluster_xxxx的命名方式

# 好友私聊：每人独立列表（可自己管理，最多10个）
MC_MOTD_PRIVATE_FRIEND_STRATEGY=personal
MC_MOTD_PERSONAL_SERVER_LIMIT=10

# 群临时会话：跟随所属群
MC_MOTD_PRIVATE_GROUP_TEMP_STRATEGY=follow_group
MC_MOTD_TRACK_USER_ACTIVITY=true
MC_MOTD_FOLLOW_GROUP_FALLBACK=personal

# 权限管理
MC_MOTD_SUPERUSERS=["123456789"]
MC_MOTD_GROUP_ADMIN_PERMISSION=true
```

#### 多群聊隔离模式 - 简化配置

```env
# 启用多群聊模式
MC_MOTD_MULTI_GROUP_MODE=true

# 好友私聊：使用全局列表（适合公共服务器）
MC_MOTD_PRIVATE_FRIEND_STRATEGY=global

# 群临时会话：跟随所属群
MC_MOTD_PRIVATE_GROUP_TEMP_STRATEGY=follow_group
```

## 使用方法

### 用户命令

| 命令             | 功能                     |
| ---------------- | ------------------------ |
| `/motd`          | 查询所有服务器状态       |
| `/motd --detail` | 显示详细信息包括玩家列表 |
| `/motd help`     | 显示帮助                 |

### 管理员命令

| 命令                                  | 功能                   | 权限要求 |
| ------------------------------------- | ---------------------- | -------- |
| `/motd add ip:port 标签`              | 添加服务器             | 管理员   |
| `/motd del ip:port`                   | 删除指定服务器         | 管理员   |
| `/motd del -rf`                       | 删除所有服务器         | 管理员   |
| `/motd render allocate ip:port 位置`  | 调整服务器显示顺序     | 管理员   |
| `/motd render swap ip1:port ip2:port` | 交换两个服务器显示顺序 | 管理员   |

### 使用示例

#### 传统模式示例

```bash
# 任何群聊
/motd add hypixel.net Hypixel服务器
/motd add play.example.com:25566 我的服务器
/motd
/motd --detail
```

#### 多群聊隔离模式示例

**在群A中：**

```bash
/motd add mc.hypixel.net Hypixel
# 添加到群A的服务器列表

/motd
# 查询群A的服务器
```

**在群B中（与群A共享）：**

```bash
/motd
# 看到与群A相同的服务器列表（因为在同一 cluster）
```

**在群C中（独立）：**

```bash
/motd
# 还没有添加任何服务器（独立列表）

/motd add localhost:25565 测试服
# 添加到群C的独立列表
```

**好友私聊（personal 模式）：**

```bash
/motd add play.myserver.com:25566 我的私人服务器
# 添加到你的个人列表（不影响任何群）

/motd
# 查询你的个人服务器列表
```

**群临时会话（follow_group 策略）：**

```bash
# 通过群A发起临时会话
/motd
# 显示群A的服务器列表

# 通过群B发起临时会话
/motd
# 显示群B的服务器列表
```

## 多群聊模式说明

### 作用域（Scope）架构

```mermaid
graph TD
    A[作用域类型] --> B[全局 global]
    A --> C[单群 group_xxx]
    A --> D[群组共享 cluster_xxx]
    A --> E[好友私聊 private_friend_xxx]
    A --> F[群临时会话 private_temp_xxx]
    
    B --> B1[传统模式/全局列表<br/>示例: global]
    C --> C1[单个群独立列表<br/>示例: group_123456]
    D --> D2[多个群共享列表<br/>示例: cluster_friends]
    E --> E1[好友私聊个人列表<br/>示例: private_friend_789]
    F --> F1[临时会话个人列表<br/>示例: private_temp_789]
```

### 权限管理架构

```mermaid
graph TD
    A[权限等级] --> B[超级管理员]
    A --> C[群管理员] 
    A --> D[普通用户]
    
    B --> B1[管理范围: 所有作用域]
    B --> B2[SUPERUSERS + MC_MOTD_SUPERUSERS]
    
    C --> C1[管理范围: 本群作用域]
    C --> C2[group_xxx 或所属 cluster_xxx]
    C --> C3[需开启 MC_MOTD_GROUP_ADMIN_PERMISSION]
    
    D --> D1[管理范围: 个人作用域]
    D --> D2[private_friend_xxx<br/>private_temp_xxx]
    D --> D3[仅在 personal 模式下]
```

### 假人过滤机制

假人过滤功能通过两种方式识别：

```mermaid
flowchart TD
    A[玩家名称] --> B{MC_MOTD_FILTER_BOTS}
    B -->|false| C[不过滤，显示所有玩家]
    B -->|true| D[启用假人过滤]
    
    D --> E[精确名称匹配]
    D --> F[正则表达式匹配]
    
    E --> E1[MC_MOTD_BOT_NAMES<br/>默认: Anonymous Player]
    F --> F1[MC_MOTD_BOT_PATTERNS<br/>匹配 player_123, bot_456 等]
    
    E1 --> G{匹配结果}
    F1 --> G
    G -->|匹配| H[标记为假人，不显示]
    G -->|不匹配| I[显示真实玩家]
```

默认正则规则会匹配：

- `player_123`、`player_456` 等
- `bot_789`、`bot_001` 等
- `fake_111`、`fake_222` 等
- `[Bot]xxx`、`[Fake]xxx` 等带标签的假人

如需关闭正则匹配但保留名称匹配，可设置：

```env
MC_MOTD_BOT_PATTERNS=[]
```

## 常见问题

**Q: 如何从传统模式切换到多群聊模式？**

A: 设置 `MC_MOTD_MULTI_GROUP_MODE=true` 即可。旧数据会自动归入 `global` 作用域，不会丢失。

**Q: 群临时会话显示"无法确定来源群"？**

A: 用户需要先在群内发言，插件才能追踪其活跃群。或将 `MC_MOTD_FOLLOW_GROUP_FALLBACK` 设为 `global` 使用全局列表。

**Q: personal 模式下如何限制用户添加服务器数量？**

A: 设置 `MC_MOTD_PERSONAL_SERVER_LIMIT`，例如 `10` 表示最多 10 个服务器，`0` 表示不限制。

**Q: 如何让多个群共享同一个服务器列表？**

A: 使用 `MC_MOTD_GROUP_CLUSTERS` 配置，例如：

```env
MC_MOTD_GROUP_CLUSTERS='{"cluster_a": ["123456", "789012"]}'
```

但是请注意，设置CLUSTERS后，原来群`"123456"`和` "789012"`设置的服务器仍然储存在各自`group_xxx`作用域内，而此时群`"123456"`和` "789012"`作用域变为`cluster_a`，此时相当于创建了一张全新的数据表。因此查询会为空白，需要重新添加服务器。

**Q: 如何设置命令前缀和参数分隔？**

A: 读取的是Nonebot全局配置，推荐项如下：

```env
COMMAND_START=["/"]
COMMAND_SEP=[" "]
```

## 注意事项

- 必须配置管理员权限后才可使用管理功能
- 多群聊模式下，普通用户在 personal 模式可管理自己的列表
- 数据库文件会自动创建在插件数据目录
- 假人过滤/显示详细信息仅对支持玩家列表的服务器有效
- 建议适当调整超时时间以适应网络环境
- 添加服务器时自动排在列表末尾，删除服务器后顺序自动调整
- 群临时会话使用 follow_group 策略需要用户在群内有发言记录

## 图片示例

![示例图片](https://aquaoh.oss-cn-shanghai.aliyuncs.com/post/image-20250925170806592.png)

