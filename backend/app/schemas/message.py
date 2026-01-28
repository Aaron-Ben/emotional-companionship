"""Enhanced message schemas with character context and emotion support."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class EmotionState(BaseModel):
    """Detected emotion state of a message."""
    primary_emotion: str = Field(..., description="Primary emotion: happy, sad, angry, neutral, etc.")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence in emotion detection")
    intensity: float = Field(default=0.5, ge=0.0, le=1.0, description="Intensity of the emotion")

    class Config:
        json_schema_extra = {
            "example": {
                "primary_emotion": "happy",
                "confidence": 0.85,
                "intensity": 0.7
            }
        }


class MessageContext(BaseModel):
    """Enhanced context for character-aware messages."""
    user_mood: Optional[EmotionState] = Field(None, description="Detected user mood/emotion")
    recent_conversation_summary: Optional[str] = Field(None, description="Summary of recent conversation")
    character_state: Dict[str, Any] = Field(default_factory=dict, description="Character's current internal state")
    should_avoid_argument: bool = Field(default=False, description="Whether to avoid arguments based on context")
    initiate_topic: bool = Field(default=False, description="Whether character should initiate a topic")

    class Config:
        json_schema_extra = {
            "example": {
                "user_mood": {
                    "primary_emotion": "sad",
                    "confidence": 0.8,
                    "intensity": 0.6
                },
                "should_avoid_argument": True,
                "character_state": {
                    "proactivity_level": 0.8,
                    "emotional_sensitivity": 0.9
                }
            }
        }


class ChatRequest(BaseModel):
    """Request for character chat."""
    message: str = Field(..., description="User's message to the character")
    character_id: str = Field(default="sister_001", description="Character to chat with")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        None, description="Previous conversation messages for context"
    )
    stream: bool = Field(default=False, description="Whether to stream the response")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "我回来了",
                "character_id": "sister_001",
                "conversation_history": [
                    {"role": "user", "content": "我出门了"},
                    {"role": "assistant", "content": "哥哥路上小心～"}
                ],
                "stream": False
            }
        }


class ChatResponse(BaseModel):
    """Response from character chat."""
    message: str = Field(..., description="Character's response message")
    character_id: str = Field(..., description="Character that generated the response")
    context_used: Optional[MessageContext] = Field(None, description="Context information used")
    emotion_detected: Optional[EmotionState] = Field(None, description="Emotion detected from user's message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "哥哥回来啦！今天过得怎么样呀？我等你等好久呢～",
                "character_id": "sister_001",
                "emotion_detected": {
                    "primary_emotion": "neutral",
                    "confidence": 0.7,
                    "intensity": 0.3
                }
            }
        }


class StreamChatResponse(BaseModel):
    """Chunk of a streaming chat response."""
    chunk: str = Field(..., description="Chunk of the response text")
    character_id: str = Field(..., description="Character generating the response")
    done: bool = Field(default=False, description="Whether this is the final chunk")


class VoiceResponse(BaseModel):
    """Response from voice input processing."""
    text: str = Field(..., description="Recognized text from voice input")
    emotion: Optional[str] = Field(None, description="Detected emotion from voice (e.g., [开心], [伤心])")
    event: Optional[str] = Field(None, description="Detected event from voice (e.g., [鼓掌], [大笑])")
    success: bool = Field(..., description="Whether recognition was successful")
    error: Optional[str] = Field(None, description="Error message if recognition failed")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "你好啊",
                "emotion": "[开心]",
                "event": None,
                "success": True
            }
        }
