"""鸣潮指令教学插件：检索鸣潮机器人指令用法，并在鸣潮话题轮次注入使用边界。

数据层（search.py / catalog.json / skills）与 Rmiao 版本同源，只替换宿主外壳。
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List

from maibot_sdk import Field, HookHandler, MaiBotPlugin, PluginConfigBase, Tool
from maibot_sdk.types import HookMode

from .search import query_help, read_skill

QUERY_TOOL = "xutheringwaves_command_help"
SKILL_TOOL = "xutheringwaves_read_skill"

# 只在确实像鸣潮话题时注入边界，避免每轮固定开销。
TOPIC_PATTERN = re.compile(
    r"鸣潮|Wuthering|库街区|波片|声骸|深塔|海墟|全息|共鸣链|练度|抽卡记录|兑换码|签到|ww",
    re.IGNORECASE,
)

SOURCE_FLAGS = (
    ("XutheringWavesUID", "xutheringwavesuid_enabled", "本体查询"),
    ("ScoreEcho", "scoreecho_enabled", "声骸评分"),
    ("RoverSign", "roversign_enabled", "库街区签到"),
)

QUERY_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "maxLength": 200, "description": "用户问题或命令；留空查看分类"},
        "source": {
            "type": "string",
            "enum": ["XutheringWavesUID", "ScoreEcho", "RoverSign"],
            "description": "可选；限定单一资料来源，留空查全部已开启来源",
        },
        "limit": {"type": "integer", "minimum": 1, "maximum": 8},
    },
    "required": ["query"],
    "additionalProperties": False,
}

SKILL_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "source": {"type": "string", "enum": ["XutheringWavesUID", "ScoreEcho", "RoverSign"]},
    },
    "required": ["source"],
    "additionalProperties": False,
}


class PluginSectionConfig(PluginConfigBase):
    """插件基础配置节，宿主据此识别配置版本。"""

    __ui_label__ = "插件"
    __ui_icon__ = "package"
    __ui_order__ = 0

    enabled: bool = Field(default=True, description="是否启用本插件")
    config_version: str = Field(default="2.0.0", description="配置版本")


class XwHelpConfig(PluginConfigBase):
    """鸣潮指令教学配置。"""

    __ui_label__ = "鸣潮指令教学"
    __ui_icon__ = "waves"
    __ui_order__ = 0

    plugin: PluginSectionConfig = Field(default_factory=PluginSectionConfig)
    xutheringwavesuid_enabled: bool = Field(default=True, description="XutheringWavesUID 作为资料来源")
    scoreecho_enabled: bool = Field(default=True, description="ScoreEcho 作为资料来源")
    roversign_enabled: bool = Field(default=True, description="RoverSign 作为资料来源")
    command_prefix: str = Field(default="ww", description="实例前缀，用于拼接示例；留空表示不加前缀")
    inject_rules: bool = Field(default=True, description="鸣潮话题轮次注入使用边界")


class XwCommandHelpPlugin(MaiBotPlugin):
    """鸣潮指令教学。"""

    config_model = XwHelpConfig

    async def on_load(self) -> None:
        """插件加载完成。"""
        self.ctx.logger.info("鸣潮指令教学已加载")

    async def on_unload(self) -> None:
        """插件卸载。"""
        self.ctx.logger.info("鸣潮指令教学已卸载")

    def _config_dict(self) -> Dict[str, Any]:
        """把强类型配置转成检索层使用的字典。"""
        return self.config.model_dump()

    @Tool(
        QUERY_TOOL,
        description=(
            "鸣潮（Wuthering Waves）机器人功能查询：XutheringWavesUID 本体查询、ScoreEcho 声骸评分、"
            "RoverSign 库街区签到，查询指令用法、参数和前置条件。用于用户询问如何使用机器人；"
            "保持当前人格口吻，不代执行。回执里的 example 已按实例前缀拼接，教学时必须原样带上前缀。"
            "来源是否可用以本次回执为准。"
        ),
        parameters=QUERY_SCHEMA,
    )
    async def handle_command_help(
        self, query: str = "", source: str = "", limit: int = 5, **kwargs: Any
    ) -> Dict[str, Any]:
        """查询已启用来源的指令条目。"""
        del kwargs
        return {"success": True, "content": query_help(self._config_dict(), query, source, limit)}

    @Tool(
        SKILL_TOOL,
        description=(
            "按需读取鸣潮指令教学的简短技能说明，不改变人格。"
            "先查询指令；需要了解某来源的使用流程时再读取。关闭来源不可读取。"
        ),
        parameters=SKILL_SCHEMA,
    )
    async def handle_read_skill(self, source: str = "", **kwargs: Any) -> Dict[str, Any]:
        """读取已启用来源的教学文档。"""
        del kwargs
        return {"success": True, "content": read_skill(self._config_dict(), source)}

    @HookHandler("maisaka.planner.before_request", mode=HookMode.BLOCKING)
    async def inject_rules(self, **kwargs: Any) -> Dict[str, Any]:
        """鸣潮话题轮次补一条使用边界，防止模型凭印象否认功能。"""
        if not self.config.plugin.enabled or not self.config.inject_rules:
            return {"action": "continue"}
        if not TOPIC_PATTERN.search(self._latest_user_text(kwargs)):
            return {"action": "continue"}
        note = self._rules_note()
        if not note:
            return {"action": "continue"}
        items = kwargs.get("items")
        if isinstance(items, list):
            self._append_system_text(items, note)
            return {"action": "continue", "modified_kwargs": kwargs}
        messages = kwargs.get("messages")
        if isinstance(messages, list):
            kwargs["messages"] = self._messages_with_system_text(messages, note)
            return {"action": "continue", "modified_kwargs": kwargs}
        return {"action": "continue"}

    def _rules_note(self) -> str:
        """生成简短规则；没有启用来源时不注入。"""
        available = [f"{name}（{label}）" for name, flag, label in SOURCE_FLAGS if self.config.model_dump().get(flag)]
        if not available:
            return ""
        prefix = str(self.config.command_prefix or "").strip()
        prefix_hint = f"示例已带前缀 `{prefix}`，原样给出。" if prefix else "本实例未配置前缀。"
        return (
            "\n\n【鸣潮功能】本轮涉及鸣潮。可用来源："
            + "、".join(available)
            + f"。需要说法时先调用 `{QUERY_TOOL}` 查询，不要凭印象说没有该功能；"
            + f"{prefix_hint}只教不执行（不代签到、不代评分、不代登录），"
            + "不索取 Cookie 或密码；资料是本地快照，不代表本群已启用或已执行成功。"
        )

    @staticmethod
    def _latest_user_text(kwargs: Dict[str, Any]) -> str:
        """从 planner 载荷里取最后一条用户文本，用于话题判定。"""
        items = kwargs.get("items")
        if isinstance(items, list):
            for item in reversed(items):
                if not isinstance(item, dict) or item.get("item_type") != "UserMessageItem":
                    continue
                texts = XwCommandHelpPlugin._texts_of(item.get("parts"))
                if texts:
                    return texts
        messages = kwargs.get("messages")
        if isinstance(messages, list):
            for message in reversed(messages):
                if isinstance(message, dict) and str(message.get("role") or "").lower() == "user":
                    content = message.get("content")
                    if isinstance(content, str):
                        return content
        return ""

    @staticmethod
    def _texts_of(parts: Any) -> str:
        """拼接 parts 中的文本片段。"""
        if not isinstance(parts, list):
            return ""
        chunks: List[str] = []
        for part in parts:
            if isinstance(part, dict) and part.get("type") == "text":
                chunks.append(str(part.get("text") or ""))
        return "\n".join(chunks)

    @staticmethod
    def _append_system_text(items: List[Any], note: str) -> None:
        """并入已有 SystemMessageItem；没有则新建一条合法 item。"""
        for item in reversed(items):
            if not isinstance(item, dict) or item.get("item_type") != "SystemMessageItem":
                continue
            parts = item.get("parts")
            if isinstance(parts, list) and parts and isinstance(parts[-1], dict) and parts[-1].get("type") == "text":
                parts[-1]["text"] = f"{parts[-1].get('text') or ''}{note}"
            elif isinstance(parts, list):
                parts.append({"type": "text", "text": note.strip()})
            else:
                item["parts"] = [{"type": "text", "text": note.strip()}]
            return
        items.insert(
            0,
            {
                "item_type": "SystemMessageItem",
                "meta": {
                    "item_id": f"xw-help-{uuid.uuid4().hex}",
                    "logical_turn_id": None,
                    "timestamp": datetime.now().isoformat(),
                },
                "parts": [{"type": "text", "text": note.strip()}],
            },
        )

    @staticmethod
    def _messages_with_system_text(messages: List[Any], note: str) -> List[Dict[str, Any]]:
        """旧 messages 契约下并入 system 消息。"""
        result = [dict(message) for message in messages if isinstance(message, dict)]
        for message in result:
            if str(message.get("role") or "").lower() == "system" and isinstance(message.get("content"), str):
                message["content"] = f"{message['content']}{note}"
                return result
        result.insert(0, {"role": "system", "content": note.strip()})
        return result
