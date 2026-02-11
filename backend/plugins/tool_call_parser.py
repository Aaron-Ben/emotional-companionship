"""
VCP format tool call parser.
Parses AI responses for <<<[TOOL_REQUEST]>>> format tool calls.
"""
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class ToolCall:
    """Tool call data structure."""
    name: str
    args: Dict[str, Any]
    archery: bool = False  # Whether this is an async call (no reply expected)


class ToolCallParser:
    """VCP format tool call parser."""

    MARKER_START = "<<<[TOOL_REQUEST]>>>"
    MARKER_END = "<<<[END_TOOL_REQUEST]>>>"

    # Parameter parsing regex: key:「始」value「末」
    PARAM_REGEX = re.compile(r'([\w_]+)\s*:\s*「始」([\s\S]*?)「末」\s*(?:,)?')

    @classmethod
    def parse(cls, content: str) -> List[ToolCall]:
        """
        Parse all tool calls in AI response.

        Args:
            content: AI response text

        Returns:
            List of parsed ToolCall objects
        """
        if not content or not isinstance(content, str):
            return []

        if cls.MARKER_START not in content:
            return []

        if cls.MARKER_END not in content:
            return []

        tool_calls = []
        search_offset = 0

        while search_offset < len(content):
            # Find tool call start marker
            start_index = content.find(cls.MARKER_START, search_offset)
            if start_index == -1:
                break

            # Find tool call end marker
            end_index = content.find(
                cls.MARKER_END,
                start_index + len(cls.MARKER_START)
            )
            if end_index == -1:
                search_offset = start_index + len(cls.MARKER_START)
                continue

            # Extract tool call content
            block_content = content[
                start_index + len(cls.MARKER_START):end_index
            ].strip()

            parsed = cls._parse_block(block_content)
            if parsed:
                tool_calls.append(parsed)

            search_offset = end_index + len(cls.MARKER_END)

        return tool_calls

    @classmethod
    def _parse_block(cls, block_content: str) -> Optional[ToolCall]:
        """
        Parse a single tool call block.

        Args:
            block_content: Content between markers

        Returns:
            ToolCall object or None if parsing failed
        """
        args = {}
        tool_name = None
        is_archery = False

        matches = cls.PARAM_REGEX.finditer(block_content)
        for match in matches:
            key, value = match.groups()
            value = value.strip()

            if key == 'tool_name':
                tool_name = value
            elif key == 'archery':
                is_archery = value in ('true', 'no_reply')
            else:
                args[key] = value

        return ToolCall(
            name=tool_name,
            args=args,
            archery=is_archery
        ) if tool_name else None

    @classmethod
    def separate(cls, tool_calls: List[ToolCall]) -> Dict[str, List[ToolCall]]:
        """
        Separate normal calls from archery (async) calls.

        Args:
            tool_calls: List of tool calls

        Returns:
            Dict with 'normal' and 'archery' lists
        """
        return {
            'normal': [tc for tc in tool_calls if not tc.archery],
            'archery': [tc for tc in tool_calls if tc.archery]
        }

    @classmethod
    def contains_tool_call(cls, content: str) -> bool:
        """
        Check if content contains any tool call markers.

        Args:
            content: Text to check

        Returns:
            True if tool call markers found
        """
        return cls.MARKER_START in content if content else False
