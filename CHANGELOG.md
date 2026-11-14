# Changelog

## 0.1.0

### 主要功能

- 移植 Rmiao「鸣潮指令教学」插件到 MaiBot：两个工具 + 一个 Planner 注入钩子。
- 数据层与 Rmiao 版本同源：`catalog.json`（146 条）、`skills/*/SKILL.md`、`search.py` 原样复用。
- 三个来源开关与实例前缀沿用；关闭的来源不出现在查询结果和注入文本里。

### 细节

- 工具默认 deferred，由 tool_search 按需发现，不常驻工具列表。
- `maisaka.planner.before_request` 钩子仅在最近一条用户消息命中鸣潮话题时注入一段边界说明。
