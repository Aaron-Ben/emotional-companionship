"""Chat service that integrates character personalities with LLM services."""

from typing import List, Dict, Optional, AsyncGenerator, Any
import random
import re
from datetime import datetime

from app.services.llm import LLM
from app.services.character_service import CharacterService
from app.services.diary import DiaryFileService
from app.models.character import UserCharacterPreference
from app.schemas.message import (
    ChatRequest,
    ChatResponse,
    MessageContext
)


class ChatService:
    """
    Enhanced chat service that integrates character personalities with LLM services.
    """

    def __init__(self, llm: LLM, character_service: CharacterService):
        """
        Initialize chat service.

        Args:
            llm: LLM instance to use for generating responses
            character_service: Character service for managing personalities
        """
        self.llm = llm
        self.character_service = character_service
        self.diary_service = DiaryFileService()

    async def chat(
        self,
        request: ChatRequest,
        user_preferences: Optional[UserCharacterPreference] = None,
        user_id: str = "user_default"
    ) -> ChatResponse:
        """
        Generate a character-aware response.

        Args:
            request: Chat request with message and character info
            user_preferences: Optional user preferences
            user_id: User ID for diary retrieval

        Returns:
            ChatResponse: Character's response with metadata
        """
        # Build message context
        message_context = self._build_message_context(request)

        # Generate system prompt with character and context
        system_prompt = self.character_service.generate_system_prompt(
            character_id=request.character_id,
            user_preferences=user_preferences,
            context=message_context.dict() if message_context else None
        )

        # Add diary context if available
        if self.diary_service:
            diary_context = await self._get_diary_context(
                character_id=request.character_id,
                user_id=user_id,
                current_message=request.message
            )
            if diary_context:
                system_prompt = self._add_diary_context_to_prompt(system_prompt, diary_context)

        # Build messages list
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history if provided
        if request.conversation_history:
            messages.extend(request.conversation_history)

        # Add current message
        messages.append({"role": "user", "content": request.message})

        # Generate response (no function calling needed)
        message_content = self.llm.generate_response(messages)

        # Build response object
        return ChatResponse(
            message=message_content,
            character_id=request.character_id,
            context_used=message_context.dict() if message_context else None,
            timestamp=datetime.now()
        )

    async def chat_stream(
        self,
        request: ChatRequest,
        user_preferences: Optional[UserCharacterPreference] = None,
        user_id: str = "user_default"
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming character-aware response.

        Args:
            request: Chat request with message and character info
            user_preferences: Optional user preferences
            user_id: User ID for diary retrieval

        Yields:
            str: Chunks of the character's response
        """
        # Build message context
        message_context = self._build_message_context(request)

        # Generate system prompt with character and context
        system_prompt = self.character_service.generate_system_prompt(
            character_id=request.character_id,
            user_preferences=user_preferences,
            context=message_context.dict() if message_context else None
        )

        # Add diary context if available
        if self.diary_service:
            diary_context = await self._get_diary_context(
                character_id=request.character_id,
                user_id=user_id,
                current_message=request.message
            )
            if diary_context:
                system_prompt = self._add_diary_context_to_prompt(system_prompt, diary_context)

        # Build messages list
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history if provided
        if request.conversation_history:
            messages.extend(request.conversation_history)

        # Add current message
        messages.append({"role": "user", "content": request.message})

        # Stream response
        for chunk in self.llm.generate_response_stream(messages):
            yield chunk

    async def _get_diary_context(
        self,
        character_id: str,
        user_id: str,
        current_message: str
    ) -> Optional[str]:
        """
        Get relevant diary entries for context.

        Args:
            character_id: Character ID (used as diary_name)
            user_id: User ID
            current_message: Current user message

        Returns:
            Formatted diary context or None
        """
        if not self.diary_service:
            return None

        try:
            # Get recent diaries for this character
            diaries = self.diary_service.list_diaries(
                diary_name=character_id,
                limit=10
            )

            if not diaries:
                return None

            # Filter for relevant diaries based on message
            relevant_diaries = self._filter_relevant_diaries(diaries, current_message)

            if not relevant_diaries:
                return None

            return self._format_diary_context(relevant_diaries[:3])
        except Exception as e:
            # Log error but don't fail the chat
            print(f"Error getting diary context: {e}")
            return None

    def _filter_relevant_diaries(self, diaries: List[Dict], message: str) -> List[Dict]:
        """
        Filter diaries for relevance to current message.

        Args:
            diaries: List of diary entries
            message: Current message

        Returns:
            List of relevant diaries
        """
        message_lower = message.lower()
        relevant = []

        for diary in diaries:
            content = diary.get("content", "")

            # Extract tags from content
            tag_match = re.search(r'Tag:\s*(.+)$', content, re.MULTILINE | re.IGNORECASE)
            if tag_match:
                tag_string = tag_match.group(1)
                tags = [tag.strip() for tag in re.split(r'[,，、]', tag_string) if tag.strip()]
                for tag in tags:
                    if tag.lower() in message_lower:
                        relevant.append(diary)
                        break

            # Check content keywords
            keywords = ["哥哥", "今天", "昨天", "开心", "难过"]
            for keyword in keywords:
                if keyword in content and keyword in message_lower:
                    relevant.append(diary)
                    break

        return relevant

    def _format_diary_context(self, diaries: List[Dict]) -> str:
        """
        Format diary entries as context.

        Args:
            diaries: List of diary entries

        Returns:
            Formatted context string
        """
        context_parts = ["## 之前的回忆\n\n"]

        for diary in diaries:
            # Extract date from filename (format: YYYY-MM-DD_HHMMSS.txt)
            path = diary.get("path", "")
            filename = path.split("/")[-1] if "/" in path else path
            date_part = filename.split("_")[0] if "_" in filename else "未知日期"

            content = diary.get("content", "")
            # Remove Tag line from context display
            content_without_tag = re.sub(r'\n\nTag:.*$', '', content, flags=re.MULTILINE | re.IGNORECASE)

            context_parts.append(f"**{date_part}的日记**\n{content_without_tag}\n")

        return "\n".join(context_parts)

    def _add_diary_context_to_prompt(self, system_prompt: str, diary_context: str) -> str:
        """
        Add diary context to system prompt.

        Args:
            system_prompt: Original system prompt
            diary_context: Formatted diary context

        Returns:
            Enhanced system prompt with diary context
        """
        return f"""{system_prompt}

{diary_context}

请参考这些回忆，在对话中可以自然地提及过去的事情，让对话更有连续性和亲切感。
但不要刻意提及，要自然融入。
"""

    def _build_message_context(
        self,
        request: ChatRequest
    ) -> Optional[MessageContext]:
        """
        Build message context based on request metadata.

        Args:
            request: Chat request

        Returns:
            MessageContext or None
        """
        # Get character to check behavior parameters
        character = self.character_service.get_character(request.character_id)

        if not character:
            return None

        character_state = {
            "proactivity_level": character.behavior.proactivity_level,
            "argument_avoidance_threshold": character.behavior.argument_avoidance_threshold
        }

        # Determine if character should initiate a topic (random based on proactivity)
        initiate_topic = random.random() < character.behavior.proactivity_level

        return MessageContext(
            character_state=character_state,
            initiate_topic=initiate_topic
        )
