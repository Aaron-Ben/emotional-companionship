"""Time extractor using LLM to identify future events from conversation."""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.llms.base import LLMBase
from app.services.temporal.models import (
    FutureEvent,
    TimeExpressionType,
    ExtractTimelineRequest,
)
from app.services.temporal.normalizer import TimeNormalizer


logger = logging.getLogger(__name__)


# LLM prompt for extracting time expressions
TIME_EXTRACTION_PROMPT = """你是一个专业的时间信息提取助手。你的任务是从对话中识别所有未来时间相关的信息。

请仔细分析以下对话，提取所有涉及未来时间的信息，包括：
1. 相对时间表达（明天、后天、下周、下个月等）
2. 具体日期（1月25日、2月14日等）
3. 模糊时间表达（一会、改天、以后等）

对于每个时间表达，请提取：
- time_expression: 原始时间表达（如"明天下午3点"）
- event_title: 相关事件标题（简短描述，如"开会"）
- event_description: 事件的详细描述（如果对话中有提供）
- context: 包含该时间表达的完整句子或上下文

如果对话中没有提到任何未来时间信息，请返回空列表。

请以JSON格式返回，格式如下：
```json
{
  "has_future_events": true/false,
  "events": [
    {
      "time_expression": "明天下午3点",
      "event_title": "开会",
      "event_description": "明天下午3点有个重要会议",
      "context": "用户说：明天下午3点开会，记得提醒我"
    }
  ]
}
```

注意：
1. 只提取未来的时间，已经过去的不要提取
2. event_title要简短明了，2-8个字
3. event_description可以包含更多细节
4. 如果时间表达不明确（如"一会"、"改天"），仍然提取但置信度会较低"""


class TimeExtractor:
    """
    Extracts future time events from conversation using LLM.

    Combines LLM understanding with rule-based normalization.
    """

    def __init__(self, llm: LLMBase):
        """
        Initialize time extractor.

        Args:
            llm: LLM instance for analyzing conversations
        """
        self.llm = llm
        self.normalizer = TimeNormalizer()

    def extract_from_conversation(
        self,
        request: ExtractTimelineRequest
    ) -> List[FutureEvent]:
        """
        Extract future events from conversation.

        Args:
            request: Timeline extraction request

        Returns:
            List of extracted FutureEvent objects
        """
        try:
            # Build conversation text for LLM
            conversation_text = self._format_conversation(request.conversation_messages)

            # Call LLM to extract time expressions
            llm_response = self._call_llm(conversation_text)

            if not llm_response or not llm_response.get("has_future_events"):
                logger.info(f"No future events found for {request.user_id}/{request.character_id}")
                return []

            # Process LLM response and normalize dates
            events = self._process_llm_response(
                llm_response.get("events", []),
                request.character_id,
                request.user_id
            )

            logger.info(
                f"Extracted {len(events)} future events for "
                f"{request.user_id}/{request.character_id}"
            )

            return events

        except Exception as e:
            logger.error(f"Error extracting time events: {e}")
            return []

    def _format_conversation(self, messages: List[Dict[str, str]]) -> str:
        """
        Format conversation messages for LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Formatted conversation text
        """
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Map roles to Chinese
            role_map = {
                "user": "用户",
                "assistant": "助手",
                "system": "系统"
            }
            role_cn = role_map.get(role, role)

            formatted.append(f"{role_cn}：{content}")

        return "\n".join(formatted)

    def _call_llm(self, conversation_text: str) -> Optional[Dict[str, Any]]:
        """
        Call LLM to extract time expressions.

        Args:
            conversation_text: Formatted conversation text

        Returns:
            LLM response dict with 'has_future_events' and 'events'
        """
        try:
            messages = [
                {"role": "system", "content": TIME_EXTRACTION_PROMPT},
                {"role": "user", "content": f"请分析以下对话中的时间信息：\n\n{conversation_text}"}
            ]

            response = self.llm.generate_response(messages=messages)

            if not response:
                return None

            # Try to parse JSON from response
            try:
                # Clean up response - remove markdown code blocks if present
                cleaned = response.strip()
                if cleaned.startswith("```"):
                    # Find the JSON content
                    lines = cleaned.split("\n")
                    json_lines = []
                    in_json = False
                    for line in lines:
                        if line.strip().startswith("```json") or line.strip() == "```":
                            in_json = not in_json
                            continue
                        if in_json or not line.startswith("```"):
                            json_lines.append(line)
                    cleaned = "\n".join(json_lines)

                parsed = json.loads(cleaned)
                return parsed

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response as JSON: {response[:200]}")
                return None

        except Exception as e:
            logger.error(f"Error calling LLM for time extraction: {e}")
            return None

    def _process_llm_response(
        self,
        llm_events: List[Dict[str, Any]],
        character_id: str,
        user_id: str
    ) -> List[FutureEvent]:
        """
        Process LLM response and normalize dates.

        Args:
            llm_events: List of event dicts from LLM
            character_id: Character ID
            user_id: User ID

        Returns:
            List of FutureEvent objects
        """
        events = []

        for event_data in llm_events:
            try:
                # Extract time expression
                time_expression = event_data.get("time_expression", "")
                if not time_expression:
                    continue

                # Normalize to absolute date
                normalized_date, expr_type, confidence = self.normalizer.normalize(time_expression)

                # Skip if no valid date and not fuzzy time
                if not normalized_date and expr_type != TimeExpressionType.FUZZY_TIME:
                    continue

                # For fuzzy time, we still want to record but with lower confidence
                if not normalized_date:
                    confidence = 0.3

                # Create FutureEvent
                event = FutureEvent(
                    character_id=character_id,
                    user_id=user_id,
                    title=event_data.get("event_title", "未命名事件"),
                    description=event_data.get("event_description", ""),
                    event_date=normalized_date or "",
                    original_expression=time_expression,
                    expression_type=expr_type,
                    confidence=confidence,
                    source_conversation=event_data.get("context", ""),
                    status="pending",
                    created_at=datetime.now()
                )

                events.append(event)

            except Exception as e:
                logger.warning(f"Error processing event data: {e}")
                continue

        return events
