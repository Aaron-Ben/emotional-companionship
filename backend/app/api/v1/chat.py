"""Chat API endpoints for character-based conversations."""

from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from datetime import datetime
import asyncio
import logging

from app.services.llms.qwen import QwenLLM
from app.services.llms.deepseek import DeepSeekLLM
from app.services.character_service import CharacterService
from app.services.chat_service import ChatService
from app.services.diary_service import DiaryService
from app.services.diary_triggers import DiaryTriggerManager
from app.models.character import UserCharacterPreference
from app.models.diary import DiaryTriggerType
from app.schemas.message import ChatRequest, ChatResponse, StreamChatResponse

# Create router
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# Configure logging
logger = logging.getLogger(__name__)

# In-memory storage for user preferences (shared with character API)
from app.api.v1.character import _user_preferences_store

# In-memory storage for diary trigger managers (key: user_id_character_id)
_diary_trigger_managers: Dict[str, DiaryTriggerManager] = {}


def get_character_service() -> CharacterService:
    """Dependency injection for CharacterService."""
    return CharacterService()


def get_llm_service() -> QwenLLM | DeepSeekLLM:
    """
    Dependency injection for LLM service.
    Uses DeepSeek-V3 by default, can be configured via environment.

    Note: Requires DASHSCOPE_API_KEY or DEEPSEEK_API_KEY environment variable.
    """
    import os

    # Check if user wants to use Qwen via environment variable
    llm_provider = os.getenv("LLM_PROVIDER", "deepseek").lower()

    if llm_provider == "qwen":
        return QwenLLM()

    # Default to DeepSeek-V3
    return DeepSeekLLM(config={"model": "deepseek-chat"})


def get_mock_user_id() -> str:
    """
    Mock user ID for development.
    In production, this would come from authentication.
    """
    return "user_default"


def get_user_preferences(
    character_id: str,
    user_id: str
) -> Optional[UserCharacterPreference]:
    """Get user preferences from store."""
    key = f"{user_id}_{character_id}"
    return _user_preferences_store.get(key)


def get_diary_service() -> DiaryService:
    """Dependency injection for DiaryService."""
    return DiaryService()


def get_trigger_manager(user_id: str, character_id: str) -> DiaryTriggerManager:
    """Get or create trigger manager for a user-character pair."""
    key = f"{user_id}_{character_id}"
    if key not in _diary_trigger_managers:
        _diary_trigger_managers[key] = DiaryTriggerManager()
    return _diary_trigger_managers[key]


async def check_and_generate_diary(
    message: str,
    character_id: str,
    user_id: str,
    response_message: str,
    emotion_detected: Optional[object],
    llm: QwenLLM | DeepSeekLLM,
    diary_service: DiaryService
):
    """
    Check if diary should be triggered and generate it.

    This runs in the background after a response is sent.
    """
    try:
        trigger_manager = get_trigger_manager(user_id, character_id)

        # Check triggers
        triggers = await trigger_manager.check_triggers(message, emotion_detected)

        if triggers:
            logger.info(f"Diary triggers detected for {user_id}/{character_id}: {[t.value for t in triggers]}")

            # Build conversation summary
            conversation_summary = f"""
            用户消息: {message}
            妹妹回复: {response_message}
            """

            # Extract emotions
            emotions = []
            if emotion_detected:
                if hasattr(emotion_detected, 'primary_emotion'):
                    emotions.append(emotion_detected.primary_emotion)
                if hasattr(emotion_detected, 'secondary_emotions'):
                    emotions.extend(emotion_detected.secondary_emotions)

            # Generate diary for each trigger type
            for trigger_type in triggers:
                try:
                    diary_entry = await diary_service.generate_diary(
                        llm=llm,
                        character_id=character_id,
                        user_id=user_id,
                        conversation_summary=conversation_summary,
                        trigger_type=trigger_type,
                        emotions=emotions,
                        context={"message": message, "response": response_message}
                    )
                    logger.info(f"Diary generated: {diary_entry.id} (trigger: {trigger_type.value})")

                    # Reset daily counter if it was a daily summary
                    if trigger_type == DiaryTriggerType.DAILY_SUMMARY:
                        trigger_manager.reset_daily()

                except Exception as e:
                    logger.error(f"Error generating diary for trigger {trigger_type.value}: {e}")

    except Exception as e:
        logger.error(f"Error in check_and_generate_diary: {e}")


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Depends(get_mock_user_id),
    character_service: CharacterService = Depends(get_character_service),
    llm: QwenLLM | DeepSeekLLM = Depends(get_llm_service),
    diary_service: DiaryService = Depends(get_diary_service)
):
    """
    Send a message to a character and get a response.

    Request Body:
    - message: User's message to the character
    - character_id: Character to chat with (default: "sister_001")
    - conversation_history: Optional previous messages for context
    - stream: Whether to stream the response (default: false)

    Returns:
        Character's response with metadata including detected emotion

    Example:
    ```json
    {
        "message": "我回来了",
        "character_id": "sister_001",
        "stream": false
    }
    ```
    """
    # Verify character exists
    character = character_service.get_character(request.character_id)
    if not character:
        raise HTTPException(
            status_code=404,
            detail=f"Character not found: {request.character_id}"
        )

    # Get user preferences if available
    user_preferences = get_user_preferences(request.character_id, user_id)

    # Create chat service with diary service
    chat_service = ChatService(
        llm=llm,
        character_service=character_service,
        diary_service=diary_service
    )

    # Generate response
    try:
        response = await chat_service.chat(
            request=request,
            user_preferences=user_preferences,
            user_id=user_id
        )

        # Trigger diary generation in background (don't wait for it)
        asyncio.create_task(
            check_and_generate_diary(
                message=request.message,
                character_id=request.character_id,
                user_id=user_id,
                response_message=response.message,
                emotion_detected=response.emotion_detected,
                llm=llm,
                diary_service=diary_service
            )
        )

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    user_id: str = Depends(get_mock_user_id),
    character_service: CharacterService = Depends(get_character_service),
    llm: QwenLLM | DeepSeekLLM = Depends(get_llm_service),
    diary_service: DiaryService = Depends(get_diary_service)
):
    """
    Send a message to a character and get a streaming response.

    Request Body is the same as the regular chat endpoint, but stream should be set to true.

    Returns:
        Server-Sent Events (SSE) stream with response chunks

    Example:
    ```json
    {
        "message": "我回来了",
        "character_id": "sister_001",
        "stream": true
    }
    ```
    """
    # Verify character exists
    character = character_service.get_character(request.character_id)
    if not character:
        raise HTTPException(
            status_code=404,
            detail=f"Character not found: {request.character_id}"
        )

    # Get user preferences if available
    user_preferences = get_user_preferences(request.character_id, user_id)

    # Create chat service with diary service
    chat_service = ChatService(
        llm=llm,
        character_service=character_service,
        diary_service=diary_service
    )

    # Store full response for diary generation
    full_response = []

    async def generate():
        """Generate streaming response."""
        nonlocal full_response
        try:
            async for chunk in chat_service.chat_stream(
                request=request,
                user_preferences=user_preferences,
                user_id=user_id
            ):
                # Send SSE format
                yield f"data: {chunk}\n\n"
                full_response.append(chunk)
            # Send completion signal
            yield "data: [DONE]\n\n"

            # Trigger diary generation after stream completes
            response_text = "".join(full_response)
            asyncio.create_task(
                check_and_generate_diary(
                    message=request.message,
                    character_id=request.character_id,
                    user_id=user_id,
                    response_message=response_text,
                    emotion_detected=None,  # Emotion detection not available in stream
                    llm=llm,
                    diary_service=diary_service
                )
            )
        except Exception as e:
            yield f"data: [ERROR: {str(e)}]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/starter")
async def get_conversation_starter(
    character_id: str = "sister_001",
    user_id: str = Depends(get_mock_user_id),
    character_service: CharacterService = Depends(get_character_service)
):
    """
    Get a conversation starter from a character.

    Query Parameters:
    - character_id: Character to get starter from (default: "sister_001")

    Returns:
        Conversation starter message
    """
    # Get user preferences if available
    user_preferences = get_user_preferences(character_id, user_id)

    # Get conversation starter
    starter = character_service.get_conversation_starter(
        character_id=character_id,
        user_preferences=user_preferences
    )

    if not starter:
        raise HTTPException(
            status_code=404,
            detail="No conversation starter available for this character"
        )

    return {
        "starter": starter,
        "character_id": character_id,
        "timestamp": datetime.now().isoformat()
    }
