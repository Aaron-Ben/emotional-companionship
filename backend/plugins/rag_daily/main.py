"""
RAGDailyPlugin - 日记检索插件

根据时间表达式从日记中检索相关内容，作为用户主入口文件。
用户可根据需要扩展此文件。
"""

from typing import Dict, Any, List, Optional
from .time_parser import TimeExpressionParser
from .group_manager import SemanticGroupManager


class RAGDailyPlugin:
    """日记检索插件主类"""

    def __init__(self):
        self.time_parser = TimeExpressionParser()
        self.group_manager: Optional[SemanticGroupManager] = None
        self.config: Dict[str, Any] = {}
        self.dependencies: Dict[str, Any] = {}
        self.initialized = False

    async def initialize(self, config: Dict[str, Any], dependencies: Dict[str, Any]) -> None:
        """
        初始化插件

        Args:
            config: 插件配置
            dependencies: 依赖注入 (如 vectorDBManager)
        """
        self.config = config
        self.dependencies = dependencies
        self.group_manager = SemanticGroupManager()
        self.initialized = True
        print("[RAGDailyPlugin] Initialized successfully")

    async def process_messages(self, messages: List[Dict], config: Dict[str, Any]) -> List[Dict]:
        """
        预处理消息 - 检测时间表达式并检索相关日记

        Args:
            messages: 消息列表
            config: 插件配置

        Returns:
            处理后的消息列表
        """
        if not self.initialized:
            return messages

        # 获取最后一条用户消息
        user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        if not user_message:
            return messages

        # 解析时间表达式
        time_ranges = self.time_parser.parse(user_message)

        if time_ranges:
            # 检测并激活语义组
            activated_groups = self.group_manager.detect_and_activate_groups(user_message)
            print(f"[RAGDailyPlugin] Found {len(time_ranges)} time range(s), {len(activated_groups)} group(s) activated")

            # TODO: 根据时间范围和语义组检索日记内容
            # 这里需要调用实际的日记检索逻辑

        return messages

    async def process_tool_call(self, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理工具调用 - 支持通过工具调用方式检索日记

        Args:
            tool_args: 工具参数，可能包含:
                - time_expression: 时间表达式
                - keyword: 搜索关键词
                - groups: 语义组过滤

        Returns:
            检索结果
        """
        if not self.initialized:
            return {
                "status": "error",
                "error": "Plugin not initialized"
            }

        time_expression = tool_args.get("time_expression", "")
        keyword = tool_args.get("keyword", "")

        # 解析时间
        time_ranges = self.time_parser.parse(time_expression)

        # 检测语义组
        activated_groups = {}
        if keyword:
            activated_groups = self.group_manager.detect_and_activate_groups(keyword)

        # TODO: 实现实际的日记检索逻辑

        return {
            "status": "success",
            "result": f"Found {len(time_ranges)} time range(s) and {len(activated_groups)} group(s)",
            "time_ranges": [{"start": tr.start.isoformat(), "end": tr.end.isoformat()} for tr in time_ranges],
            "activated_groups": list(activated_groups.keys())
        }

    async def shutdown(self) -> None:
        """关闭插件，清理资源"""
        # 保存语义组状态
        if self.group_manager:
            await self.group_manager.save_groups()
        print("[RAGDailyPlugin] Shutdown complete")


# 插件实例 (由 PluginManager 加载)
_plugin_instance: Optional[RAGDailyPlugin] = None


def initialize(config: Dict[str, Any], dependencies: Dict[str, Any]) -> None:
    """同步初始化入口 (兼容性)"""
    import asyncio
    global _plugin_instance
    _plugin_instance = RAGDailyPlugin()
    # 使用 asyncio.create_task 或同步方式初始化
    # 这里简化处理，实际应根据环境调整


async def initialize_async(config: Dict[str, Any], dependencies: Dict[str, Any]) -> None:
    """异步初始化入口"""
    global _plugin_instance
    _plugin_instance = RAGDailyPlugin()
    await _plugin_instance.initialize(config, dependencies)


async def process_messages(messages: List[Dict], config: Dict[str, Any]) -> List[Dict]:
    """消息预处理器入口"""
    global _plugin_instance
    if _plugin_instance is None:
        # 自动初始化
        _plugin_instance = RAGDailyPlugin()
    return await _plugin_instance.process_messages(messages, config)


async def process_tool_call(tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """工具调用入口"""
    global _plugin_instance
    if _plugin_instance is None:
        return {"status": "error", "error": "Plugin not initialized"}
    return await _plugin_instance.process_tool_call(tool_args)


async def shutdown() -> None:
    """关闭入口"""
    global _plugin_instance
    if _plugin_instance:
        await _plugin_instance.shutdown()


# 默认使用异步初始化
initialize = initialize_async
