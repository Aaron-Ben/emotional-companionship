"""
VCP format tool executor.
Executes parsed tool calls and formats results.
"""
import logging
from typing import Dict, Any, List
from .tool_call_parser import ToolCall


# Configure detailed logging
logger = logging.getLogger(__name__)


class ToolExecutor:
    """Tool executor for running plugin tool calls."""

    def __init__(self, plugin_manager):
        """
        Initialize tool executor.

        Args:
            plugin_manager: PluginManager instance for executing tools
        """
        self.plugin_manager = plugin_manager
        self.logger = logger

    async def execute(self, tool_call: ToolCall, client_ip: str = None) -> Dict[str, Any]:
        """
        Execute a single tool call.

        Args:
            tool_call: ToolCall to execute
            client_ip: Optional client IP for logging

        Returns:
            {
                'success': bool,
                'content': Any,  # Formatted content
                'raw': Any,     # Original result
                'tool_name': str,
                'error': str      # Error message (on failure)
            }
        """
        tool_name = tool_call.name
        args = tool_call.args

        self.logger.info(f"[ToolExecutor] Executing tool: {tool_name}")
        self.logger.info(f"[ToolExecutor] Args: {args}")

        # Check if plugin exists
        if tool_name not in self.plugin_manager.plugins:
            self.logger.error(f"[ToolExecutor] Plugin not found: {tool_name}")
            self.logger.info(f"[ToolExecutor] Available plugins: {list(self.plugin_manager.plugins.keys())}")
            return self._create_error_result(
                tool_name,
                f"未找到名为 \"{tool_name}\" 的插件"
            )

        # Execute plugin
        try:
            self.logger.info(f"[ToolExecutor] Calling plugin_manager.process_tool_call({tool_name}, ...)")
            result = await self.plugin_manager.process_tool_call(tool_name, args)
            self.logger.info(f"[ToolExecutor] Plugin returned: {result}")
            return self._process_result(tool_name, result)
        except Exception as e:
            self.logger.error(f"[ToolExecutor] Tool execution error [{tool_name}]: {e}", exc_info=True)
            return self._create_error_result(
                tool_name,
                f"执行错误: {str(e)}"
            )

    async def execute_all(self, tool_calls: List[ToolCall], client_ip: str = None) -> List[Dict]:
        """
        Execute multiple tool calls.

        Args:
            tool_calls: List of ToolCall objects
            client_ip: Optional client IP

        Returns:
            List of execution result dicts
        """
        return [
            await self.execute(tc, client_ip)
            for tc in tool_calls
        ]

    def _process_result(self, tool_name: str, result: Dict) -> Dict:
        """
        Process tool execution result.

        Args:
            tool_name: Name of the tool
            result: Raw result from plugin

        Returns:
            Formatted result dict
        """
        success = result.get('status') == 'success'

        if not success:
            return self._create_error_result(
                tool_name,
                result.get('error', '未知错误')
            )

        # Get return content
        raw_result = result.get('result')

        # Check if rich content format
        if isinstance(raw_result, dict) and 'content' in raw_result:
            content = raw_result['content']
        else:
            content = raw_result

        return {
            'success': True,
            'content': content,
            'raw': result,
            'tool_name': tool_name
        }

    def _create_error_result(self, tool_name: str, message: str) -> Dict:
        """
        Create an error result dict.

        Args:
            tool_name: Name of the tool
            message: Error message

        Returns:
            Error result dict
        """
        return {
            'success': False,
            'error': message,
            'content': f"[错误] {message}",
            'tool_name': tool_name
        }

    @staticmethod
    def format_tool_results(execution_results: List[Dict]) -> str:
        """
        Format tool execution results for injection into conversation.

        Args:
            execution_results: List of execution result dicts

        Returns:
            Formatted summary string
        """
        summary_parts = ["[[VCP调用结果信息汇总"]

        for result in execution_results:
            tool_name = result.get('tool_name', 'Unknown')
            if result['success']:
                content = str(result.get('content', ''))
                # Truncate long content
                if len(content) > 1000:
                    content = content[:1000] + "..."
                summary_parts.append(f"- 工具名称: {tool_name}")
                summary_parts.append(f"- 执行状态: success")
                summary_parts.append(f"- 返回内容: {content}")
            else:
                summary_parts.append(f"- 工具名称: {tool_name}")
                summary_parts.append(f"- 执行状态: failed")
                summary_parts.append(f"- 错误信息: {result.get('error', '未知错误')}")

        summary_parts.append("VCP调用结果结束]]")
        return "\n".join(summary_parts)
