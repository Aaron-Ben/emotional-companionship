"""Character API request/response schemas - Simplified for file system based storage."""

from typing import List
from pydantic import BaseModel, Field

from app.models.character import UserCharacter


class CreateCharacterRequest(BaseModel):
    """Request to create a new character."""
    name: str = Field(..., min_length=1, max_length=100, description="Character name")
    prompt: str = Field(..., min_length=1, description="System prompt for the character")


class UpdateCharacterPromptRequest(BaseModel):
    """Request to update a character's prompt."""
    prompt: str = Field(..., min_length=1, description="New system prompt")


class UserCharacterListResponse(BaseModel):
    """Response with list of user characters."""
    characters: List[UserCharacter]
    count: int


class UserCharacterResponse(BaseModel):
    """Response with a single user character."""
    character: UserCharacter
