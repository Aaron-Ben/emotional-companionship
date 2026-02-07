"""Chat API endpoints for character-based conversations."""

from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from datetime import datetime
import asyncio
import logging

from app.services.llm import LLM
from app.services.character_service import CharacterService
from app.services.chat_service import ChatService
from app.services.temporal import TimeExtractor, EventRetriever
from app.models.character import UserCharacterPreference
from app.schemas.message import ChatRequest, ChatResponse, VoiceResponse, TTSRequest, TTSResponse

# Create router
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# Configure logging
logger = logging.getLogger(__name__)

# In-memory storage for user preferences (shared with character API)
from app.api.v1.character import _user_preferences_store


def get_character_service() -> CharacterService:
    """Dependency injection for CharacterService."""
    return CharacterService()


def get_llm_service() -> LLM:
    """
    Dependency injection for LLM service.
    Uses OpenRouter by default.

    Note: Requires OPENROUTER_API_KEY environment variable.
    """
    import os

    # Get model from environment or use default
    model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")

    return LLM(config={"model": model})


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


async def extract_and_save_diary(
    character_id: str,
    user_id: str,
    conversation_messages: List[Dict[str, str]],
    llm: LLM
):
    """
    Extract and save diary from conversation (async).

    This runs in the background after a response is sent.
    AI will evaluate if the conversation is worth recording and extract diary content.

    Args:
        character_id: Character ID (used as diary_name)
        user_id: User ID
        conversation_messages: Current conversation messages
        llm: LLM instance for evaluation and extraction
    """
    try:
        logger.info(f"Evaluating diary extraction for {user_id}/{character_id}")

        # Build conversation text for evaluation
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in conversation_messages
        ])

        # Step 1: Evaluate if worth recording and what action to take
        evaluation_prompt = f"""分析以下对话，判断应该如何处理日记。

对话内容：
{conversation_text}

请只回答以下选项之一：
- "CREATE" - 需要创建新日记（对话包含新的重要信息）
- "UPDATE" - 需要更新已有日记（对话提到修正或补充之前的记录）
- "SKIP" - 不需要记录（对话内容不重要）

判断标准：
1. 包含新的重要信息 → CREATE
2. 提到修正、补充、更新之前的记录 → UPDATE
3. 无关紧要的内容 → SKIP

如果选择 UPDATE，请用格式：UPDATE | 原内容片段 | 新内容片段
如果选择 CREATE 或 SKIP，只需返回选项本身。

示例：
- CREATE
- UPDATE | 哥哥去了北京出差 | 哥哥去了上海出差
- SKIP"""

        evaluation = llm.generate_response([
            {"role": "system", "content": "你是一个日记记录助手，负责判断如何处理日记。"},
            {"role": "user", "content": evaluation_prompt}
        ])

        logger.info(f"Diary evaluation: {evaluation}")

        if "SKIP" in evaluation.upper() or "跳过" in evaluation:
            logger.info(f"Diary evaluation: skipped for {user_id}/{character_id}")
            return

        from app.services.diary.file_service import DiaryFileService
        from datetime import datetime

        diary_service = DiaryFileService()

        # Step 2: Handle UPDATE case
        if "UPDATE" in evaluation.upper():
            # Parse evaluation to extract target and replace content
            parts = evaluation.split("|")
            if len(parts) == 3:
                target = parts[1].strip()
                replace_content = parts[2].strip()

                # Use update_diary
                result = diary_service.update_diary(
                    target=target,
                    replace=replace_content,
                    diary_name=character_id
                )

                if result["status"] == "success":
                    logger.info(f"Diary updated successfully: {result['path']}")
                else:
                    logger.warning(f"Diary update failed: {result['message']}")
            else:
                logger.warning(f"Invalid UPDATE format: {evaluation}")
            return

        # Step 3: Handle CREATE case
        diary_prompt = f"""根据以下对话，提取日记内容。

对话内容：
{conversation_text}

请按照以下格式生成日记：

【对话主题】简述本次对话的核心内容

【对话记录】
哥哥：...
我：...

【关键信息】
- 要点1
- 要点2

【我的感受】

Tag: 关键词1, 关键词2, 关键词3

注意：
1. 日记要简洁，突出重点
2. Tag 要包含3-5个关键词
3. 只返回日记内容，不要其他解释"""

        diary_content = llm.generate_response([
            {"role": "system", "content": "你是一个日记记录助手，负责从对话中提取日记内容。"},
            {"role": "user", "content": diary_prompt}
        ])

        # Step 4: Create new diary
        today = datetime.now().strftime("%Y-%m-%d")

        result = diary_service.create_diary(
            diary_name=character_id,
            date=today,
            content=diary_content
        )

        if result["status"] == "success":
            logger.info(f"Diary created successfully: {result['data']['path']}")
        else:
            logger.error(f"Failed to create diary: {result['message']}")

    except Exception as e:
        logger.error(f"Error extracting/saving diary: {e}")


async def extract_and_save_timeline(
    character_id: str,
    user_id: str,
    conversation_messages: List[Dict[str, str]],
    llm: LLM
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
    llm: LLM = Depends(get_llm_service)
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

        # Build current conversation ONLY (不包括历史，避免日记内容重复)
        # 日记应该只记录本次对话的新增内容
        conversation_messages = [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": response.message}
        ]

        # Trigger async diary extraction (AI will judge if worth recording)
        asyncio.create_task(
            extract_and_save_diary(
                character_id=request.character_id,
                user_id=user_id,
                conversation_messages=conversation_messages,
                llm=llm
            )
        )

        # Always trigger async timeline extraction (don't wait for it)
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
    llm: LLM = Depends(get_llm_service)
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
            conversation_messages = [
                {"role": "user", "content": request.message},
                {"role": "assistant", "content": response_text}
            ]
            asyncio.create_task(
                extract_and_save_diary(
                    character_id=request.character_id,
                    user_id=user_id,
                    conversation_messages=conversation_messages,
                    llm=llm
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


@router.post("/voice", response_model=VoiceResponse)
async def voice_input(
    audio: UploadFile = File(..., description="Audio file (WAV format, 16kHz, mono)"),
    character_id: str = Form(default="sister_001", description="Character to chat with"),
):
    """
    Process voice input and return recognized text.

    This endpoint accepts an audio file (WAV format), performs speech recognition,
    and optionally detects emotion and events from the audio.

    Request:
    - audio: WAV audio file (16kHz, mono, 16-bit)
    - character_id: Character to chat with (default: "sister_001")

    Returns:
        Recognized text with optional emotion and event markers

    Example emotion markers: [开心], [伤心], [愤怒], [厌恶], [惊讶]
    Example event markers: [鼓掌], [大笑], [哭], [打喷嚏], [咳嗽], [深呼吸]

    The audio should be in WAV format with:
    - Sample rate: 16000 Hz
    - Channels: 1 (mono)
    - Bit depth: 16-bit
    """
    import os
    import time

    backend_start = time.time()

    try:
        # Read audio data
        read_start = time.time()
        audio_data = await audio.read()
        read_time = (time.time() - read_start) * 1000
        logger.info(f"[ASR Backend] 接收音频: {read_time:.0f}ms, 大小: {len(audio_data)} bytes")

        # Check if audio data is valid
        if len(audio_data) < 1000:
            return VoiceResponse(
                text="",
                success=False,
                error="Audio file too short or empty"
            )

        # Use ASR module for recognition
        from app.characters.asr import recognize_audio, ASR_MODEL_PATH

        # Check if model is configured
        if ASR_MODEL_PATH is None or not os.path.exists(ASR_MODEL_PATH):
            return VoiceResponse(
                text="",
                success=False,
                error="ASR model not configured. Please set up the model first."
            )

        # Perform recognition
        asr_start = time.time()
        result = recognize_audio(audio_data=audio_data)
        asr_time = (time.time() - asr_start) * 1000

        backend_total = (time.time() - backend_start) * 1000
        logger.info(f"[ASR Backend] 识别完成: {asr_time:.0f}ms, 总后端耗时: {backend_total:.0f}ms")

        # Parse result to extract emotion and event
        text = result
        emotion = None
        event = None

        # Extract emotion markers
        for emo in ["[开心]", "[伤心]", "[愤怒]", "[厌恶]", "[惊讶]"]:
            if emo in result:
                emotion = emo
                text = text.replace(emo, "")
                break

        # Extract event markers
        for evt in ["[鼓掌]", "[大笑]", "[哭]", "[打喷嚏]", "[咳嗽]", "[深呼吸]"]:
            if evt in result:
                event = evt
                text = text.replace(evt, "")
                break

        # Clean up text
        text = text.strip()

        if not text:
            return VoiceResponse(
                text="",
                emotion=emotion,
                event=event,
                success=False,
                error="No speech detected or recognition failed"
            )

        return VoiceResponse(
            text=text,
            emotion=emotion,
            event=event,
            success=True
        )

    except RuntimeError as e:
        # Model or dependency error
        return VoiceResponse(
            text="",
            success=False,
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing voice input: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing voice input: {str(e)}")


@router.post("/voice/chat")
async def voice_chat(
    audio: UploadFile = File(..., description="Audio file (WAV format, 16kHz, mono)"),
    character_id: str = Form(default="sister_001", description="Character to chat with"),
    conversation_history: Optional[str] = Form(default=None, description="JSON string of conversation history"),
    stream: bool = Form(default=False, description="Whether to stream the response"),
):
    """
    Process voice input and get character response.

    This is a convenience endpoint that combines voice recognition and chat.
    It accepts an audio file, performs speech recognition, and sends the
    recognized text to the character for a response.

    Request:
    - audio: WAV audio file (16kHz, mono, 16-bit)
    - character_id: Character to chat with (default: "sister_001")
    - conversation_history: JSON string of previous messages (optional)
    - stream: Whether to stream the response (default: false)

    Returns:
        Character's response to the voice input

    For non-streaming:
        Returns ChatResponse with the character's reply

    For streaming:
        Returns SSE stream with response chunks
    """
    import json

    try:
        # First, perform voice recognition
        voice_response = await voice_input(
            audio=audio,
            character_id=character_id
        )

        if not voice_response.success:
            raise HTTPException(
                status_code=400,
                detail=f"Voice recognition failed: {voice_response.error}"
            )

        # Combine recognized text with emotion/event markers
        message = voice_response.text or ""
        if voice_response.emotion:
            message = voice_response.emotion + message
        if voice_response.event:
            message = voice_response.event + message

        # Parse conversation history
        history = None
        if conversation_history:
            try:
                history = json.loads(conversation_history)
            except json.JSONDecodeError:
                pass

        # Create chat request
        chat_request = ChatRequest(
            message=message,
            character_id=character_id,
            conversation_history=history,
            stream=stream
        )

        # If streaming, use the stream endpoint
        if stream:
            # Import here to avoid circular dependency
            user_id = get_mock_user_id()
            character_service = get_character_service()
            llm = get_llm_service()

            return await chat_stream(
                request=chat_request,
                user_id=user_id,
                character_service=character_service,
                llm=llm
            )

        # Non-streaming: use the regular chat endpoint
        user_id = get_mock_user_id()
        character_service = get_character_service()
        llm = get_llm_service()

        return await chat(
            request=chat_request,
            user_id=user_id,
            character_service=character_service,
            llm=llm
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in voice_chat: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing voice chat: {str(e)}")


@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(
    request: TTSRequest,
):
    """
    Convert text to speech using Genie-TTS (GPT-SoVITS).

    This endpoint uses Genie-TTS for high-quality speech synthesis.
    Supports Chinese, English, Japanese, and Korean.

    Request Body:
    - text: Text to synthesize (required)
    - engine: TTS engine to use, "genie" (default: "genie")
    - character_id: Character ID for voice selection (default: "sister_001")

    Available predefined characters:
    - feibi: 菲比 (Chinese)
    - mika: 聖園ミカ (Japanese)
    - 37: ThirtySeven (English)

    Returns:
        Audio file path that can be retrieved via /api/v1/chat/tts/audio/{filename}

    Example:
    ```json
    {
        "text": "你好，哥哥！",
        "engine": "genie",
        "character_id": "sister_001"
    }
    ```
    """
    import os
    import uuid

    try:
        # Import TTS module
        from app.characters.tts import synthesize, VOICE_CACHE_PATH, DEFAULT_CHARACTER

        # Map character_id to genie character name
        character_map = {
            "sister_001": "feibi",  # 妹妹角色使用菲比的声音（中文）
        }
        character_name = character_map.get(request.character_id, DEFAULT_CHARACTER)

        # Generate unique filename for this request
        os.makedirs(os.path.dirname(VOICE_CACHE_PATH), exist_ok=True)
        filename = f"tts_{uuid.uuid4().hex[:8]}.wav"
        output_path = os.path.join(os.path.dirname(VOICE_CACHE_PATH), filename)

        # Synthesize speech
        result_path = synthesize(
            text=request.text,
            character_name=character_name,
            output_path=output_path,
            engine=request.engine or "genie",
            language="zh"
        )

        # Check if synthesis was successful
        if result_path and os.path.exists(result_path):
            return TTSResponse(
                success=True,
                audio_path=f"/api/v1/chat/tts/audio/{filename}",
                engine=request.engine or "genie"
            )
        else:
            return TTSResponse(
                success=False,
                audio_path=None,
                error="Speech synthesis failed - no audio file generated",
                engine=request.engine or "genie"
            )

    except RuntimeError as e:
        # Model or dependency error
        return TTSResponse(
            success=False,
            audio_path=None,
            error=str(e),
            engine=request.engine or "genie"
        )
    except ValueError as e:
        # Invalid engine parameter
        return TTSResponse(
            success=False,
            audio_path=None,
            error=str(e),
            engine=request.engine or "genie"
        )
    except Exception as e:
        logger.error(f"Error in text_to_speech: {e}")
        raise HTTPException(status_code=500, detail=f"Error synthesizing speech: {str(e)}")


@router.get("/tts/audio/{filename}")
async def get_tts_audio(filename: str):
    """
    Retrieve a generated TTS audio file.

    Path Parameters:
    - filename: Name of the audio file (e.g., "tts_abc12345.wav")

    Returns:
        Audio file in WAV format
    """
    import os
    from fastapi.responses import FileResponse
    from app.characters.tts import VOICE_CACHE_PATH

    # Security check: ensure filename is safe
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Construct full path
    file_path = os.path.join(os.path.dirname(VOICE_CACHE_PATH), filename)

    # Check if file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    # Return file
    return FileResponse(
        path=file_path,
        media_type="audio/wav",
        filename=filename
    )
