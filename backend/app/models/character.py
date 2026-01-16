"""Character data models for the emotional companionship system."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class CharacterTrait(str, Enum):
    """Character personality traits."""
    AFFECTIONATE = "affectionate"
    PLAYFUL = "playful"
    CARING = "caring"
    OPINIONATED = "opinionated"
    JEALOUS = "sometimes_jealous"
    PROACTIVE = "proactive"
    SHY = "shy"
    ENERGETIC = "energetic"


class CharacterType(str, Enum):
    """Types of characters."""
    EMOTIONAL_COMPANION = "emotional_companion"
    MENTOR = "mentor"
    FRIEND = "friend"


class SpeakingStyle(BaseModel):
    """Speaking style configuration."""
    affectionate_markers: List[str] = Field(default_factory=list)
    common_phrases: Dict[str, List[str]] = Field(default_factory=dict)
    tone_variations: Dict[str, Dict[str, str]] = Field(default_factory=dict)


class BehavioralParameters(BaseModel):
    """Character behavioral parameters."""
    proactivity_level: float = Field(default=0.8, ge=0.0, le=1.0)
    jealousy_frequency: float = Field(default=0.3, ge=0.0, le=1.0)
    opinionatedness: float = Field(default=0.7, ge=0.0, le=1.0)
    emotional_sensitivity: float = Field(default=0.9, ge=0.0, le=1.0)
    argument_avoidance_threshold: float = Field(default=0.6, ge=0.0, le=1.0)


class CharacterIdentity(BaseModel):
    """Character identity information."""
    role: str
    age: int
    personality_traits: List[CharacterTrait]
    description: str


class SystemPromptConfig(BaseModel):
    """System prompt configuration."""
    base: str
    variables: List[str] = Field(default_factory=list)


class ConversationExample(BaseModel):
    """Few-shot conversation example."""
    context: str
    user: str
    assistant: str


class CharacterMetadata(BaseModel):
    """Character metadata."""
    version: str
    created_at: str
    author: str
    tags: List[str] = Field(default_factory=list)


class CharacterTemplate(BaseModel):
    """Complete character template loaded from YAML."""
    character_id: str
    name: str
    base_nickname: str
    character_type: CharacterType
    identity: CharacterIdentity
    system_prompt: SystemPromptConfig
    speaking_style: SpeakingStyle
    behavior: BehavioralParameters
    conversation_starters: List[str] = Field(default_factory=list)
    examples: List[ConversationExample] = Field(default_factory=list)
    metadata: CharacterMetadata

    class Config:
        use_enum_values = True


class UserCharacterPreference(BaseModel):
    """User's personalized character preferences."""
    user_id: str
    character_id: str
    nickname: Optional[str] = None  # User's preferred nickname (overrides base_nickname)
    style_level: float = Field(default=1.0, ge=0.7, le=1.3)  # Maturity adjustment
    custom_instructions: Optional[str] = None  # Additional instructions
    relationship_notes: Optional[str] = None  # Notes about relationship
    created_at: str
    updated_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "character_id": "sister_001",
                "nickname": "亲爱的哥哥",
                "style_level": 1.1,
                "custom_instructions": "特别喜欢聊游戏相关的话题",
                "relationship_notes": "关系很亲密，经常开玩笑"
            }
        }
