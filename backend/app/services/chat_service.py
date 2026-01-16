"""Chat service that integrates character personalities with LLM services."""

from typing import List, Dict, Optional, AsyncGenerator, Any
import random
from datetime import datetime

from app.services.llms.base import LLMBase
from app.services.character_service import CharacterService
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

    async def chat(
        self,
        request: ChatRequest,
        user_preferences: Optional[UserCharacterPreference] = None
    ) -> ChatResponse:
        """
        Generate a character-aware response.

        Args:
            request: Chat request with message and character info
            user_preferences: Optional user preferences

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

        # Build messages list
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history if provided
        if request.conversation_history:
            messages.extend(request.conversation_history)

        # Add current message
        messages.append({"role": "user", "content": request.message})

        # Generate response
        response = self.llm.generate_response(messages)

        # Build response object
        return ChatResponse(
            message=response,
            character_id=request.character_id,
            context_used=message_context.dict() if message_context else None,
            emotion_detected=emotion_state,
            timestamp=datetime.now()
        )

    async def chat_stream(
        self,
        request: ChatRequest,
        user_preferences: Optional[UserCharacterPreference] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming character-aware response.

        Args:
            request: Chat request with message and character info
            user_preferences: Optional user preferences

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
