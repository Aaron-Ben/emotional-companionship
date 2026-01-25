"""Chat API endpoints for character-based conversations."""

from typing import Optional, Dict, List, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from datetime import datetime
import asyncio
import logging

from app.services.llms.qwen import QwenLLM
from app.services.llms.deepseek import DeepSeekLLM
from app.services.character_service import CharacterService
from app.services.chat_service import ChatService
from app.services.diary import DiaryCoreService, DiaryAssessmentService
from app.services.temporal import TimeExtractor, EventRetriever
from app.models.character import UserCharacterPreference
from app.schemas.message import ChatRequest, ChatResponse, StreamChatResponse, DiaryAssessment

# Create router
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# Configure logging
logger = logging.getLogger(__name__)

# In-memory storage for user preferences (shared with character API)
from app.api.v1.character import _user_preferences_store


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


def get_diary_core_service() -> DiaryCoreService:
    """Dependency injection for DiaryCoreService."""
    return DiaryCoreService()


async def extract_and_save_diary(
    character_id: str,
    user_id: str,
    conversation_messages: List[Dict[str, str]],
    diary_assessment: DiaryAssessment,
    llm: QwenLLM | DeepSeekLLM,
    diary_service: DiaryCoreService
):
    """
    Extract and save diary from actual conversation (async).

    This runs in the background after a response is sent.
    Only called when AI determines the conversation is worth recording.
    """
    try:
        if not diary_assessment.should_record:
            return

        logger.info(
            f"Extracting diary for {user_id}/{character_id}: "
            f"category={diary_assessment.category}, "
            f"reason={diary_assessment.reason}"
        )

        await diary_service.generate_from_conversation(
            llm=llm,
            character_id=character_id,
            user_id=user_id,
            conversation_messages=conversation_messages,
            assessment=diary_assessment
        )

        logger.info(f"Diary extracted and saved for {user_id}/{character_id}")

    except Exception as e:
        logger.error(f"Error extracting diary: {e}")


async def extract_and_save_timeline(
    character_id: str,
    user_id: str,
    conversation_messages: List[Dict[str, str]],
    llm: QwenLLM | DeepSeekLLM
):
    """
    Extract and save timeline events from conversation (async).

    This runs in the background after a response is sent.
    Automatically extracts future events mentioned in the conversation.
    """
    try:
        from app.services.temporal.models import ExtractTimelineRequest

        logger.info(f"Extracting timeline events for {user_id}/{character_id}")

        # Create timeline extraction request
        timeline_request = ExtractTimelineRequest(
            character_id=character_id,
            user_id=user_id,
            conversation_messages=conversation_messages
        )

        # Extract events using LLM
        extractor = TimeExtractor(llm)
        events = extractor.extract_from_conversation(timeline_request)

        if events:
            # Save events to database
            retriever = EventRetriever()
            retriever.save_events(events)
            logger.info(f"Timeline extracted and saved {len(events)} events for {user_id}/{character_id}")
        else:
            logger.info(f"No timeline events found for {user_id}/{character_id}")

    except Exception as e:
        logger.error(f"Error extracting timeline: {e}")


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Depends(get_mock_user_id),
    character_service: CharacterService = Depends(get_character_service),
    llm: QwenLLM | DeepSeekLLM = Depends(get_llm_service),
    diary_core_service: DiaryCoreService = Depends(get_diary_core_service)
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
    chat_service = ChatService(
        llm=llm,
        character_service=character_service
    )

    # Generate response
    try:
        response = await chat_service.chat(
            request=request,
            user_preferences=user_preferences,
            user_id=user_id
        )

        # If AI assessed this conversation as worth recording, extract diary asynchronously
        if response.diary_assessment and response.diary_assessment.should_record:
            # Build current conversation ONLY (不包括历史，避免日记内容重复)
            # 日记应该只记录本次对话的新增内容
            conversation_messages = [
                {"role": "user", "content": request.message},
                {"role": "assistant", "content": response.message}
            ]

            # Trigger async diary extraction (don't wait for it)
            asyncio.create_task(
                extract_and_save_diary(
                    character_id=request.character_id,
                    user_id=user_id,
                    conversation_messages=conversation_messages,
                    diary_assessment=response.diary_assessment,
                    llm=llm,
                    diary_service=diary_core_service
                )
            )

        # Always trigger async timeline extraction (don't wait for it)
        conversation_messages = [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": response.message}
        ]
        asyncio.create_task(
            extract_and_save_timeline(
                character_id=request.character_id,
                user_id=user_id,
                conversation_messages=conversation_messages,
                llm=llm
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
    diary_core_service: DiaryCoreService = Depends(get_diary_core_service)
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
    chat_service = ChatService(
        llm=llm,
        character_service=character_service
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
                assess_and_extract_diary_stream(
                    character_id=request.character_id,
                    user_id=user_id,
                    conversation_history=request.conversation_history,
                    user_message=request.message,
                    assistant_response=response_text,
                    llm=llm,
                    diary_core_service=diary_core_service
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


async def assess_and_extract_diary_stream(
    character_id: str,
    user_id: str,
    conversation_history: Optional[List[Dict[str, str]]],
    user_message: str,
    assistant_response: str,
    llm: QwenLLM | DeepSeekLLM,
    diary_core_service: DiaryCoreService
):
    """
    评估对话并提取日记（用于流式端点）。
    """
    try:
        # 构建当前对话 ONLY（不包括历史，避免日记内容重复）
        # 日记应该只记录本次对话的新增内容
        conversation_messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_response}
        ]

        # AI评估
        assessment_service = DiaryAssessmentService()
        assessment_messages = [
            {"role": "system", "content": assessment_service.build_assessment_prompt()},
            {"role": "user", "content": f"请评估以下对话是否值得记录进日记：\n\n" + "\n".join([f"{m['role']}: {m['content']}" for m in conversation_messages])}
        ]

        assessment_tool = assessment_service.get_assessment_tool()
        response = llm.generate_response(messages=assessment_messages, tools=[assessment_tool], tool_choice="auto")

        # 提取评估结果
        diary_assessment = None
        if isinstance(response, dict) and "tool_calls" in response:
            for tool_call in response.get("tool_calls", []):
                if tool_call.get("name") == "assess_diary_worthiness":
                    diary_assessment = DiaryAssessment(**tool_call.get("arguments", {}))
                    break

        # 如果值得记录，提取并保存日记
        if diary_assessment and diary_assessment.should_record:
            await diary_core_service.generate_from_conversation(
                llm=llm,
                character_id=character_id,
                user_id=user_id,
                conversation_messages=conversation_messages,
                assessment=diary_assessment
            )

        # Always extract timeline events
        await extract_and_save_timeline(
            character_id=character_id,
            user_id=user_id,
            conversation_messages=conversation_messages,
            llm=llm
        )

    except Exception as e:
        logger.error(f"Error in assess_and_extract_diary_stream: {e}")


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
