"""API schemas for chat history and topic management."""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class CreateTopicRequest(BaseModel):
    """Request to create a new chat topic."""
    character_uuid: Optional[str] = Field(None, description="Character UUID (if not provided, character_id is used)")
    character_id: Optional[str] = Field(None, description="Character ID (will be mapped to UUID)")

    class Config:
        json_schema_extra = {
            "example": {
                "character_id": "sister_001"
            }
        }


class TopicResponse(BaseModel):
    """Response for a single topic."""
    topic_id: int = Field(..., description="Topic ID (Unix timestamp)")
    character_uuid: str = Field(..., description="Character UUID")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")
    message_count: int = Field(..., description="Number of messages")

    class Config:
        json_schema_extra = {
            "example": {
                "topic_id": 1707523200,
                "character_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2024-02-10T00:00:00",
                "updated_at": "2024-02-10T01:00:00",
                "message_count": 10
            }
        }


class TopicListResponse(BaseModel):
    """Response for listing topics."""
    topics: List[TopicResponse] = Field(default_factory=list, description="List of topics")
    total: int = Field(..., description="Total number of topics")

    class Config:
        json_schema_extra = {
            "example": {
                "topics": [
                    {
                        "topic_id": 1707523200,
                        "character_uuid": "550e8400-e29b-41d4-a716-446655440000",
                        "created_at": "2024-02-10T00:00:00",
                        "updated_at": "2024-02-10T01:00:00",
                        "message_count": 10
                    }
                ],
                "total": 1
            }
        }


class ChatMessageResponse(BaseModel):
    """Response for a single chat message."""
    message_id: str = Field(..., description="Unique message ID")
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg-abc123",
                "role": "user",
                "content": "你好",
                "timestamp": "2024-02-10T00:00:00"
            }
        }


class ChatHistoryResponse(BaseModel):
    """Response for chat history."""
    topic_id: int = Field(..., description="Topic ID")
    character_uuid: str = Field(..., description="Character UUID")
    messages: List[ChatMessageResponse] = Field(default_factory=list, description="List of messages")
    total: int = Field(..., description="Total number of messages")

    class Config:
        json_schema_extra = {
            "example": {
                "topic_id": 1707523200,
                "character_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "messages": [
                    {
                        "message_id": "msg-abc123",
                        "role": "user",
                        "content": "你好",
                        "timestamp": "2024-02-10T00:00:00"
                    }
                ],
                "total": 1
            }
        }


class DeleteTopicResponse(BaseModel):
    """Response for deleting a topic."""
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Result message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Topic deleted successfully"
            }
        }
