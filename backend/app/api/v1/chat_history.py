"""Chat history API endpoints for topic and message management."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
import logging

from app.services.chat_history_service import ChatHistoryService, CharacterMappingService
from app.schemas.chat_history import (
    CreateTopicRequest,
    TopicResponse,
    TopicListResponse,
    ChatHistoryResponse,
    ChatMessageResponse,
    DeleteTopicResponse
)
from app.models.chat import ChatMessage
from datetime import datetime

# Create router
router = APIRouter(prefix="/api/v1/chat/topics", tags=["chat-history"])

# Configure logging
logger = logging.getLogger(__name__)


def get_mock_user_id() -> str:
    """Mock user ID for development. In production, this would come from authentication."""
    return "user_default"


def get_chat_history_service() -> ChatHistoryService:
    """Dependency injection for ChatHistoryService."""
    return ChatHistoryService()


@router.post("", response_model=TopicResponse)
async def create_topic(
    request: CreateTopicRequest,
    user_id: str = Depends(get_mock_user_id),
    service: ChatHistoryService = Depends(get_chat_history_service)
):
    """
    Create a new chat topic.

    Request Body:
    - character_id: Character ID (e.g., "sister_001") - will be mapped to UUID
    - character_uuid: Character UUID (optional, takes precedence over character_id)

    Returns:
        Created topic information with topic_id (Unix timestamp)

    Example:
    ```json
    {
        "character_id": "sister_001"
    }
    ```
    """
    try:
        # Resolve character UUID
        character_uuid = request.character_uuid
        if character_uuid is None:
            if request.character_id is None:
                raise HTTPException(
                    status_code=400,
                    detail="Either character_id or character_uuid must be provided"
                )
            character_uuid = service.mapping_service.get_or_create_mapping(request.character_id)

        # Create topic
        topic_id = service.create_topic(user_id, character_uuid)

        # Get topic info
        topics = service.list_topics(user_id, character_uuid)
        topic = next((t for t in topics if t.topic_id == topic_id), None)

        if topic is None:
            raise HTTPException(status_code=500, detail="Failed to create topic")

        return TopicResponse(
            topic_id=topic.topic_id,
            character_uuid=topic.character_uuid,
            created_at=datetime.fromtimestamp(topic.created_at),
            updated_at=datetime.fromtimestamp(topic.updated_at),
            message_count=topic.message_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating topic: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating topic: {str(e)}")


@router.get("", response_model=TopicListResponse)
async def list_topics(
    character_uuid: Optional[str] = None,
    character_id: Optional[str] = None,
    user_id: str = Depends(get_mock_user_id),
    service: ChatHistoryService = Depends(get_chat_history_service)
):
    """
    List chat topics for a user.

    Query Parameters:
    - character_uuid: Filter by character UUID
    - character_id: Filter by character ID (will be mapped to UUID)

    Returns:
        List of topics sorted by update time (newest first)

    Example:
    GET /api/v1/chat/topics?character_id=sister_001
    """
    try:
        # Resolve character UUID
        filter_uuid = character_uuid
        if filter_uuid is None and character_id is not None:
            filter_uuid = service.mapping_service.get_character_uuid(character_id)

        # List topics
        topics = service.list_topics(user_id, filter_uuid)

        return TopicListResponse(
            topics=[
                TopicResponse(
                    topic_id=t.topic_id,
                    character_uuid=t.character_uuid,
                    created_at=datetime.fromtimestamp(t.created_at),
                    updated_at=datetime.fromtimestamp(t.updated_at),
                    message_count=t.message_count
                )
                for t in topics
            ],
            total=len(topics)
        )

    except Exception as e:
        logger.error(f"Error listing topics: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing topics: {str(e)}")


@router.delete("/{topic_id}", response_model=DeleteTopicResponse)
async def delete_topic(
    topic_id: int,
    character_uuid: Optional[str] = None,
    user_id: str = Depends(get_mock_user_id),
    service: ChatHistoryService = Depends(get_chat_history_service)
):
    """
    Delete a chat topic.

    Path Parameters:
    - topic_id: Topic ID (Unix timestamp)

    Query Parameters:
    - character_uuid: Optional character UUID for validation

    Returns:
        Success status

    Example:
    DELETE /api/v1/chat/topics/1707523200
    """
    try:
        success = service.delete_topic(user_id, topic_id, character_uuid)

        if success:
            return DeleteTopicResponse(
                success=True,
                message=f"Topic {topic_id} deleted successfully"
            )
        else:
            return DeleteTopicResponse(
                success=False,
                message=f"Topic {topic_id} not found"
            )

    except Exception as e:
        logger.error(f"Error deleting topic: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting topic: {str(e)}")


@router.get("/{topic_id}/history", response_model=ChatHistoryResponse)
async def get_topic_history(
    topic_id: int,
    character_uuid: Optional[str] = None,
    user_id: str = Depends(get_mock_user_id),
    service: ChatHistoryService = Depends(get_chat_history_service)
):
    """
    Get chat history for a topic.

    Path Parameters:
    - topic_id: Topic ID (Unix timestamp)

    Query Parameters:
    - character_uuid: Optional character UUID (required if topic not in default location)

    Returns:
        Chat history with messages

    Example:
    GET /api/v1/chat/topics/1707523200/history
    """
    try:
        # Get topic to find character_uuid if not provided
        if character_uuid is None:
            topics = service.list_topics(user_id)
            topic = next((t for t in topics if t.topic_id == topic_id), None)
            if topic is None:
                raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")
            character_uuid = topic.character_uuid

        # Get messages
        messages = service.get_topic_history(user_id, topic_id, character_uuid)

        return ChatHistoryResponse(
            topic_id=topic_id,
            character_uuid=character_uuid,
            messages=[
                ChatMessageResponse(
                    message_id=msg.message_id,
                    role=msg.role,
                    content=msg.content,
                    timestamp=datetime.fromtimestamp(msg.timestamp)
                )
                for msg in messages
            ],
            total=len(messages)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting topic history: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting topic history: {str(e)}")


@router.get("/mappings/resolve")
async def resolve_character_mapping(
    character_id: str,
    service: ChatHistoryService = Depends(get_chat_history_service)
):
    """
    Resolve character_id to character_uuid.

    Query Parameters:
    - character_id: Character ID to resolve

    Returns:
        Character UUID (existing or newly created)

    Example:
    GET /api/v1/chat/topics/mappings/resolve?character_id=sister_001
    """
    try:
        character_uuid = service.mapping_service.get_or_create_mapping(character_id)
        return {
            "character_id": character_id,
            "character_uuid": character_uuid
        }
    except Exception as e:
        logger.error(f"Error resolving mapping: {e}")
        raise HTTPException(status_code=500, detail=f"Error resolving mapping: {str(e)}")
