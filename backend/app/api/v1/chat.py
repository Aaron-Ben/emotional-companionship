"""Chat API endpoints for character-based conversations."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from datetime import datetime

from app.services.llms.qwen import QwenLLM
from app.services.llms.deepseek import DeepSeekLLM
from app.services.character_service import CharacterService
from app.services.chat_service import ChatService
from app.models.character import UserCharacterPreference
from app.schemas.message import ChatRequest, ChatResponse, StreamChatResponse

# Create router
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# In-memory storage for user preferences (shared with character API)
from app.api.v1.character import _user_preferences_store


def get_character_service() -> CharacterService:
    """Dependency injection for CharacterService."""
    return CharacterService()


def get_llm_service() -> QwenLLM | DeepSeekLLM:
    """
    Dependency injection for LLM service.
    Uses Qwen by default, can be configured via environment.

    Note: Requires DASHSCOPE_API_KEY or DEEPSEEK_API_KEY environment variable.
    """
    import os
    # For now, default to Qwen
    # In production, this would be configurable
    return QwenLLM()


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


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Depends(get_mock_user_id),
    character_service: CharacterService = Depends(get_character_service),
    llm: QwenLLM | DeepSeekLLM = Depends(get_llm_service)
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

    # Create chat service
    chat_service = ChatService(llm=llm, character_service=character_service)

    # Generate response
    try:
        response = await chat_service.chat(
            request=request,
            user_preferences=user_preferences
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    user_id: str = Depends(get_mock_user_id),
    character_service: CharacterService = Depends(get_character_service),
    llm: QwenLLM | DeepSeekLLM = Depends(get_llm_service)
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

    # Create chat service
    chat_service = ChatService(llm=llm, character_service=character_service)

    async def generate():
        """Generate streaming response."""
        try:
            async for chunk in chat_service.chat_stream(
                request=request,
                user_preferences=user_preferences
            ):
                # Send SSE format
                yield f"data: {chunk}\n\n"
            # Send completion signal
            yield "data: [DONE]\n\n"
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
