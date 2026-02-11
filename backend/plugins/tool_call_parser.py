"""
VCP format tool call parser.
Parses AI responses for <<<[TOOL_REQUEST]>>> format tool calls.
"""
import re
import json
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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
            logger.debug(f"[ToolCallParser] Parse called with invalid content: {type(content)}")
            return []

        logger.debug(f"[ToolCallParser] Parsing content (length: {len(content)})")
        logger.debug(f"[ToolCallParser] Content preview: {content[:200]}...")

        # Check if markers exist
        if cls.MARKER_START not in content:
            logger.debug(f"[ToolCallParser] No start marker found in content")
            return []

        if cls.MARKER_END not in content:
            logger.debug(f"[ToolCallParser] Start marker found but no end marker")
            return []

        tool_calls = []
        search_offset = 0

        while search_offset < len(content):
            # Find tool call start marker
            start_index = content.find(cls.MARKER_START, search_offset)
            if start_index == -1:
                logger.debug(f"[ToolCallParser] No more start markers found")
                break

            # Find tool call end marker
            end_index = content.find(
                cls.MARKER_END,
                start_index + len(cls.MARKER_START)
            )
            if end_index == -1:
                logger.debug(f"[ToolCallParser] Start marker at {start_index} has no matching end marker")
                search_offset = start_index + len(cls.MARKER_START)
                continue

            # Extract tool call content
            block_content = content[
                start_index + len(cls.MARKER_START):end_index
            ].strip()

            logger.debug(f"[ToolCallParser] Extracted block content: {block_content}")
            parsed = cls._parse_block(block_content)
            if parsed:
                tool_calls.append(parsed)
                logger.info(f"[ToolCallParser] Successfully parsed tool call: {parsed.name} with args {parsed.args}")
            else:
                logger.warning(f"[ToolCallParser] Failed to parse block: {block_content}")

            search_offset = end_index + len(cls.MARKER_END)

        logger.info(f"[ToolCallParser] Parse complete: found {len(tool_calls)} tool call(s)")
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

        logger.debug(f"[ToolCallParser] _parse_block called with: {block_content}")

        matches = cls.PARAM_REGEX.finditer(block_content)
        match_count = 0
        for match in matches:
            match_count += 1
            key, value = match.groups()
            value = value.strip()
            logger.debug(f"[ToolCallParser] Match {match_count}: key='{key}', value='{value}'")

            if key == 'tool_name':
                tool_name = value
            elif key == 'archery':
                is_archery = value in ('true', 'no_reply')
            else:
                args[key] = value

        logger.debug(f"[ToolCallParser] _parse_block result: tool_name={tool_name}, args={args}, matches_found={match_count}")

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
