"""Character API endpoints for managing characters and user preferences."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from app.services.character_service import CharacterService
from app.models.character import CharacterType, UserCharacterPreference
from app.schemas.character import (
    CharacterResponse,
    CharacterListResponse,
    UserPreferenceCreate,
    UserPreferenceUpdate,
    UserPreferenceResponse,
    ConversationStarterRequest,
    ConversationStarterResponse
)

# Create router
router = APIRouter(prefix="/api/v1/character", tags=["character"])

# In-memory storage for user preferences (in production, use a database)
_user_preferences_store: dict = {}


def get_character_service() -> CharacterService:
    """
    Dependency injection for CharacterService.
    In production, this would be properly initialized in main.py.
    """
    # For now, create a new instance each time
    # In production, use a singleton from app state
    return CharacterService()


def get_mock_user_id() -> str:
    """
    Mock user ID for development.
    In production, this would come from authentication.
    """
    return "user_default"


@router.get("/", response_model=CharacterListResponse)
async def list_characters(
    character_type: Optional[CharacterType] = None,
    service: CharacterService = Depends(get_character_service)
):
    """
    List all available character templates.

    Query Parameters:
    - character_type: Optional filter by character type (emotional_companion, mentor, friend)

    Returns:
        List of character templates with count
    """
    characters = service.list_characters(character_type=character_type)

    return CharacterListResponse(
        characters=characters,
        count=len(characters)
    )


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: str,
    service: CharacterService = Depends(get_character_service)
):
    """
    Get a specific character template by ID.

    Path Parameters:
    - character_id: Unique character identifier (e.g., "sister_001")

    Returns:
        Character template details

    Raises:
        404: If character not found
    """
    character = service.get_character(character_id)

    if not character:
        raise HTTPException(status_code=404, detail=f"Character not found: {character_id}")

    return CharacterResponse(character=character)


@router.put("/preferences", response_model=UserPreferenceResponse)
async def upsert_user_preferences(
    preferences: UserPreferenceCreate,
    user_id: str = Depends(get_mock_user_id),
    service: CharacterService = Depends(get_character_service)
):
    """
    Create or update user preferences for a character.

    Request Body:
    - character_id: Character to customize
    - nickname: Preferred nickname (optional)
    - style_level: Maturity level 0.7-1.3 (optional, default=1.0)
    - custom_instructions: Additional instructions (optional)
    - relationship_notes: Relationship context notes (optional)

    Returns:
        Created or updated user preferences
    """
    # Check if character exists
    character = service.get_character(preferences.character_id)
    if not character:
        raise HTTPException(status_code=404, detail=f"Character not found: {preferences.character_id}")

    # Create or update user preference
    key = f"{user_id}_{preferences.character_id}"
    existing = _user_preferences_store.get(key)

    now = datetime.now().isoformat()

    user_preference = UserCharacterPreference(
        user_id=user_id,
        character_id=preferences.character_id,
        nickname=preferences.nickname,
        style_level=preferences.style_level,
        custom_instructions=preferences.custom_instructions,
        relationship_notes=preferences.relationship_notes,
        created_at=existing.created_at if existing else now,
        updated_at=now
    )

    # Save to in-memory store
    _user_preferences_store[key] = user_preference

    return UserPreferenceResponse(preference=user_preference)


@router.get("/preferences/{character_id}", response_model=UserPreferenceResponse)
async def get_user_preferences(
    character_id: str,
    user_id: str = Depends(get_mock_user_id),
    service: CharacterService = Depends(get_character_service)
):
    """
    Get user preferences for a specific character.

    Path Parameters:
    - character_id: Character to get preferences for

    Returns:
        User preferences or default if not set
    """
    # Get from store
    key = f"{user_id}_{character_id}"
    preference = _user_preferences_store.get(key)

    # If not found, return default
    if not preference:
        character = service.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail=f"Character not found: {character_id}")

        now = datetime.now().isoformat()
        preference = UserCharacterPreference(
            user_id=user_id,
            character_id=character_id,
            nickname=character.base_nickname,
            style_level=1.0,
            created_at=now,
            updated_at=now
        )

    return UserPreferenceResponse(preference=preference)


@router.delete("/preferences/{character_id}")
async def delete_user_preferences(
    character_id: str,
    user_id: str = Depends(get_mock_user_id)
):
    """
    Delete user preferences for a character (revert to defaults).

    Path Parameters:
    - character_id: Character to delete preferences for

    Returns:
        Success message
    """
    key = f"{user_id}_{character_id}"

    if key in _user_preferences_store:
        del _user_preferences_store[key]

    return {"message": "Preferences deleted successfully", "character_id": character_id}


@router.post("/starter", response_model=ConversationStarterResponse)
async def get_conversation_starter(
    request: ConversationStarterRequest,
    user_id: str = Depends(get_mock_user_id),
    service: CharacterService = Depends(get_character_service)
):
    """
    Get a conversation starter for a character.

    Request Body:
    - character_id: Character to get starter for (default: "sister_001")

    Returns:
        Conversation starter message
    """
    # Get user preferences if available
    key = f"{user_id}_{request.character_id}"
    user_preferences = _user_preferences_store.get(key)

    # Get conversation starter
    starter = service.get_conversation_starter(
        character_id=request.character_id,
        user_preferences=user_preferences
    )

    if not starter:
        raise HTTPException(status_code=404, detail="No conversation starter available for this character")

    return ConversationStarterResponse(
        starter=starter,
        character_id=request.character_id
    )
