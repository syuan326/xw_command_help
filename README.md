# 鸣潮指令教学（MaiBot）

把鸣潮（Wuthering Waves）机器人指令的用法教给群聊模型，只讲不执行。

数据来源为本地快照：XutheringWavesUID 3.8.1 / ScoreEcho 1.0.0 / RoverSign 3.0.0，共 146 条。

## 组件

| 类型 | 名称 | 作用 |
| --- | --- | --- |
| Tool | `xutheringwaves_command_help` | 按关键词检索指令条目，返回名称、说明、示例（已拼前缀）、别名、前置条件 |
| Tool | `xutheringwaves_read_skill` | 读取某来源的流程文档（`skills/<来源>/SKILL.md`） |
| Hook | `maisaka.planner.before_request` | 最近一条用户消息命中鸣潮话题时，注入一段使用边界 |

两个工具默认 deferred（未声明 `visibility`），由 `tool_search` 按需发现，不常驻工具列表。

## 配置（`config.toml`，加载时自动生成）

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `plugin.enabled` | true | 总开关 |
| `xutheringwavesuid_enabled` | true | 本体查询作为来源 |
| `scoreecho_enabled` | true | 声骸评分作为来源 |
| `roversign_enabled` | true | 库街区签到作为来源 |
| `command_prefix` | `ww` | 示例前缀；留空表示不加 |
| `inject_rules` | true | 是否在鸣潮话题轮次注入边界 |

## 边界

- 只描述指令，不导入 GsCore、不代执行、不收集 cookie/token。
- 快照不代表 GsCore 已加载、本群已启用或执行成功。
- 三个来源关闭后，两侧都不再返回对应内容。
