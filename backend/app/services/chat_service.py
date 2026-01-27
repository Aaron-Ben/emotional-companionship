"""Chat service that integrates character personalities with LLM services."""

from typing import List, Dict, Optional, AsyncGenerator, Any
import random
from datetime import datetime

from app.services.llms.base import LLMBase
from app.services.character_service import CharacterService
from app.services.diary import DiaryCoreService
from app.models.character import UserCharacterPreference
from app.schemas.message import (
    ChatRequest,
    ChatResponse,
    EmotionState,
    MessageContext
)


class ChatService:
    """
    Enhanced chat service that integrates character personalities with LLM services.
    """

    def __init__(self, llm: LLMBase, character_service: CharacterService):
        """
        Initialize chat service.

        Args:
            llm: LLM instance to use for generating responses
            character_service: Character service for managing personalities
        """
        self.llm = llm
        self.character_service = character_service
        self.diary_core_service = DiaryCoreService()

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
        # Analyze user message for emotion/context
        emotion_state = self._detect_emotion(request.message)

        # Build message context
        message_context = self._build_message_context(
            emotion_state,
            request
        )

        # Generate system prompt with character and context
        system_prompt = self.character_service.generate_system_prompt(
            character_id=request.character_id,
            user_preferences=user_preferences,
            context=message_context.dict() if message_context else None
        )

        # Add diary context if available
        if self.diary_core_service:
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
            emotion_detected=emotion_state,
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
        # Analyze user message for emotion/context
        emotion_state = self._detect_emotion(request.message)

        # Build message context
        message_context = self._build_message_context(
            emotion_state,
            request
        )

        # Generate system prompt with character and context
        system_prompt = self.character_service.generate_system_prompt(
            character_id=request.character_id,
            user_preferences=user_preferences,
            context=message_context.dict() if message_context else None
        )

        # Add diary context if available
        if self.diary_core_service:
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
            character_id: Character ID
            user_id: User ID
            current_message: Current user message

        Returns:
            Formatted diary context or None
        """
        if not self.diary_core_service:
            return None

        try:
            relevant_diaries = await self.diary_core_service.get_relevant_diaries(
                character_id=character_id,
                user_id=user_id,
                current_message=current_message,
                limit=3
            )

            if not relevant_diaries:
                return None

            return self._format_diary_context(relevant_diaries)
        except Exception as e:
            # Log error but don't fail the chat
            print(f"Error getting diary context: {e}")
            return None

    def _format_diary_context(self, diaries: List) -> str:
        """
        Format diary entries as context.

        Args:
            diaries: List of diary entries

        Returns:
            Formatted context string
        """
        context_parts = ["## 之前的回忆\n\n"]

        for diary in diaries:
            context_parts.append(f"**{diary.date}的日记**\n{diary.content}\n")

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

    def _detect_emotion(self, message: str) -> Optional[EmotionState]:
        """
        Detect emotion from user message.

        This is a simplified rule-based implementation.
        In production, you might use a dedicated emotion detection model
        or sentiment analysis service.

        Args:
            message: User's message

        Returns:
            EmotionState: Detected emotion or None
        """
        message_lower = message.lower()

        # Simple keyword-based emotion detection
        # In production, replace with actual emotion detection model

        anger_keywords = ["气死", "烦死", "讨厌", "滚", "混蛋", "去死", "气死我了", "烦死了"]
        sadness_keywords = ["难过", "伤心", "累", "痛苦", "想哭", "郁闷", "不开心", "难过", "难过死了"]
        happiness_keywords = ["开心", "高兴", "快乐", "哈哈", "太棒了", "成功", "好开心", "好激动"]
        excitement_keywords = ["哇", "太好了", "厉害", "棒", "激动", "兴奋"]

        # Check for anger
        for keyword in anger_keywords:
            if keyword in message:
                return EmotionState(
                    primary_emotion="angry",
                    confidence=0.75,
                    intensity=0.7
                )

        # Check for sadness
        for keyword in sadness_keywords:
            if keyword in message:
                return EmotionState(
                    primary_emotion="sad",
                    confidence=0.75,
                    intensity=0.6
                )

        # Check for happiness
        for keyword in happiness_keywords:
            if keyword in message:
                return EmotionState(
                    primary_emotion="happy",
                    confidence=0.8,
                    intensity=0.7
                )

        # Check for excitement
        for keyword in excitement_keywords:
            if keyword in message:
                return EmotionState(
                    primary_emotion="excited",
                    confidence=0.75,
                    intensity=0.75
                )

        # Default neutral
        return EmotionState(
            primary_emotion="neutral",
            confidence=0.6,
            intensity=0.3
        )

    def _build_message_context(
        self,
        emotion_state: Optional[EmotionState],
        request: ChatRequest
    ) -> Optional[MessageContext]:
        """
        Build message context based on emotion and request metadata.

        Args:
            emotion_state: Detected emotion state
            request: Chat request

        Returns:
            MessageContext or None
        """
        if not emotion_state:
            return None

        # Determine if arguments should be avoided
        should_avoid = emotion_state.primary_emotion in ["angry", "very_sad", "frustrated"]

        # Get character to check behavior parameters
        character = self.character_service.get_character(request.character_id)

        character_state = {}
        if character:
            character_state = {
                "proactivity_level": character.behavior.proactivity_level,
                "emotional_sensitivity": character.behavior.emotional_sensitivity,
                "argument_avoidance_threshold": character.behavior.argument_avoidance_threshold
            }

        # Determine if character should initiate a topic
        initiate_topic = (
            emotion_state.primary_emotion == "neutral" and
            character and
            random.random() < character.behavior.proactivity_level
        )

        return MessageContext(
            user_mood=emotion_state,
            character_state=character_state,
            should_avoid_argument=should_avoid,
            initiate_topic=initiate_topic
        )
