"""Enhanced message schemas with character context support."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class MessageContext(BaseModel):
    """Enhanced context for character-aware messages."""
    recent_conversation_summary: Optional[str] = Field(None, description="Summary of recent conversation")
    character_state: Dict[str, Any] = Field(default_factory=dict, description="Character's current internal state")
    initiate_topic: bool = Field(default=False, description="Whether character should initiate a topic")



class ChatRequest(BaseModel):
    """Request for character chat."""
    message: str = Field(..., description="User's message to the character")
    character_id: str = Field(default="00000000-0000-0000-0000-000000000000", description="Character to chat with")
    topic_id: Optional[int] = Field(None, description="Topic ID for continuing a conversation")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        None, description="Previous conversation messages for context"
    )
    stream: bool = Field(default=False, description="Whether to stream the response")


class ChatResponse(BaseModel):
    """Response from character chat."""
    message: str = Field(..., description="Character's response message")
    character_id: str = Field(..., description="Character that generated the response")
    topic_id: Optional[int] = Field(None, description="Topic ID for the conversation")
    context_used: Optional[MessageContext] = Field(None, description="Context information used")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class StreamChatResponse(BaseModel):
    """Chunk of a streaming chat response."""
    chunk: str = Field(..., description="Chunk of the response text")
    character_id: str = Field(..., description="Character generating the response")
    done: bool = Field(default=False, description="Whether this is the final chunk")
