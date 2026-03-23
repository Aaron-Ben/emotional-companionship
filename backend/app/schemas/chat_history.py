"""API schemas for chat history and topic management."""

from typing import List
from pydantic import BaseModel, Field
from datetime import datetime

# Import models to reuse definitions
from app.models.chat import ChatMessage

# Reuse ChatMessage from models for API responses
# This eliminates duplication and ensures consistency
ChatMessageResponse = ChatMessage


class CreateTopicRequest(BaseModel):
    """Request to create a new chat topic."""
    character_id: str = Field(..., description="Character ID")


class TopicResponse(BaseModel):
    """Response for a single topic."""
    topic_id: int = Field(..., description="Topic ID (Unix timestamp)")
    character_id: str = Field(..., description="Character ID")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")
    message_count: int = Field(..., description="Number of messages")


class TopicListResponse(BaseModel):
    """Response for listing topics."""
    topics: List[TopicResponse] = Field(default_factory=list, description="List of topics")
    total: int = Field(..., description="Total number of topics")


class ChatHistoryResponse(BaseModel):
    """Response for chat history."""
    topic_id: int = Field(..., description="Topic ID")
    character_id: str = Field(..., description="Character ID")
    messages: List[ChatMessageResponse] = Field(default_factory=list, description="List of messages")
    total: int = Field(..., description="Total number of messages")

class DeleteTopicResponse(BaseModel):
    """Response for deleting a topic."""
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Result message")
