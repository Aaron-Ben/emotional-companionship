"""Chat history data models for message and topic management."""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class ChatMessage(BaseModel):
    """Single message in a chat conversation."""
    message_id: str = Field(default_factory=lambda: f"msg-{uuid.uuid4().hex}", description="Unique message ID")
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp()), description="Unix timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg-abc123",
                "role": "user",
                "content": "你好",
                "timestamp": 1707523200
            }
        }


class ChatTopic(BaseModel):
    """Topic information metadata."""
    topic_id: int = Field(..., description="Topic ID (Unix timestamp)")
    character_uuid: str = Field(..., description="Character UUID")
    created_at: int = Field(..., description="Creation timestamp (from filesystem)")
    updated_at: int = Field(..., description="Last update timestamp (from filesystem)")
    message_count: int = Field(..., description="Number of messages in topic")

    class Config:
        json_schema_extra = {
            "example": {
                "topic_id": 1707523200,
                "character_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": 1707523200,
                "updated_at": 1707526800,
                "message_count": 10
            }
        }


class ChatHistory(BaseModel):
    """Chat history containing a list of messages."""
    messages: List[ChatMessage] = Field(default_factory=list, description="List of chat messages")

    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {
                        "message_id": "msg-abc123",
                        "role": "user",
                        "content": "你好",
                        "timestamp": 1707523200
                    },
                    {
                        "message_id": "msg-def456",
                        "role": "assistant",
                        "content": "哥哥回来啦！",
                        "timestamp": 1707523201
                    }
                ]
            }
        }
