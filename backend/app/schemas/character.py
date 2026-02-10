"""Character API request/response schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.models.character import CharacterTemplate, UserCharacterPreference, CharacterType


class CharacterResponse(BaseModel):
    """Response with character template."""
    character: CharacterTemplate


class CharacterListResponse(BaseModel):
    """Response with list of characters."""
    characters: List[CharacterTemplate]
    count: int


class UserPreferenceCreate(BaseModel):
    """Request to create user preferences."""
    character_id: str = Field(..., description="Character ID to customize")
    nickname: Optional[str] = Field(None, description="Preferred nickname for character to address user")
    style_level: float = Field(1.0, ge=0.7, le=1.3, description="Maturity level (0.7=more playful, 1.3=more mature)")
    custom_instructions: Optional[str] = Field(None, description="Additional instructions for the character")
    relationship_notes: Optional[str] = Field(None, description="Notes about the relationship context")



class UserPreferenceUpdate(BaseModel):
    """Request to update user preferences."""
    character_id: str = Field(..., description="Character ID to update")
    nickname: Optional[str] = Field(None, description="New nickname")
    style_level: Optional[float] = Field(None, ge=0.7, le=1.3, description="New maturity level")
    custom_instructions: Optional[str] = Field(None, description="New instructions")
    relationship_notes: Optional[str] = Field(None, description="New notes")



class UserPreferenceResponse(BaseModel):
    """Response with user preferences."""
    preference: UserCharacterPreference


class ConversationStarterRequest(BaseModel):
    """Request for a conversation starter."""
    character_id: str = Field(default="sister_001", description="Character to get starter for")



class ConversationStarterResponse(BaseModel):
    """Response with conversation starter."""
    starter: str
    character_id: str
