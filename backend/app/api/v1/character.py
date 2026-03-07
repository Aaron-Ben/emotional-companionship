"""Character API endpoints - Simplified for file system based storage.

Characters are stored as:
- data/characters/{uuid}/prompt.md - Character system prompt
- data/characters/{uuid}/topics/ - Conversation topics
- data/characters/{uuid}/.character_meta.json - Metadata (name, created_at, updated_at)
- data/daily/{name}/ - Diary files (global directory organized by name)
"""

from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Depends

from app.services.character_service import CharacterStorageService
from app.services.chat_history_service import ChatHistoryService
from app.schemas.character import (
    CreateCharacterRequest,
    UpdateCharacterPromptRequest,
    CharacterListResponse,
    CharacterResponse,
)

# Create router
router = APIRouter(prefix="/api/v1/character", tags=["character"])

# Global character storage service instance
_character_storage_service: Optional[CharacterStorageService] = None

# User preferences store (for backward compatibility, currently empty)
_user_preferences_store: Dict[str, any] = {}


def get_character_storage_service() -> CharacterStorageService:
    """Get or create the character storage service singleton."""
    global _character_storage_service
    if _character_storage_service is None:
        _character_storage_service = CharacterStorageService()
    return _character_storage_service


def get_chat_history_service() -> ChatHistoryService:
    """Get chat history service instance."""
    return ChatHistoryService()


def get_mock_user_id() -> str:
    """Mock user ID for development."""
    return "user_default"


# ----------------------------------------------------------------------
# User Character Management Endpoints
# ----------------------------------------------------------------------

@router.post("/create", response_model=CharacterResponse, status_code=201)
async def create_character(
    request: CreateCharacterRequest,
    storage: CharacterStorageService = Depends(get_character_storage_service),
    history_service: ChatHistoryService = Depends(get_chat_history_service)
):
    """Create a new character with name and prompt."""
    try:
        character = storage.create_character(request.name, request.prompt)
        # Auto-create a topic for the new character
        user_id = get_mock_user_id()
        topic_id = history_service.create_topic(user_id, character.character_id)
        return CharacterResponse(character=character)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create character: {str(e)}")


@router.get("/user/list", response_model=CharacterListResponse)
async def list_user_characters(
    storage: CharacterStorageService = Depends(get_character_storage_service)
):
    """List all user-created characters."""
    characters = storage.list_characters()
    return CharacterListResponse(characters=characters, count=len(characters))


@router.get("/user/{character_id}", response_model=CharacterResponse)
async def get_user_character(
    character_id: str,
    storage: CharacterStorageService = Depends(get_character_storage_service)
):
    """Get a user character by ID (UUID)."""
    character = storage.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail=f"Character not found: {character_id}")
    return CharacterResponse(character=character)


@router.delete("/user/{character_id}")
async def delete_user_character(
    character_id: str,
    storage: CharacterStorageService = Depends(get_character_storage_service)
):
    """Delete a user character."""
    success = storage.delete_character(character_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Character not found: {character_id}")
    return {"message": "Character deleted successfully", "character_id": character_id}


@router.patch("/user/{character_id}", response_model=CharacterResponse)
async def update_user_character_prompt(
    character_id: str,
    request: UpdateCharacterPromptRequest,
    storage: CharacterStorageService = Depends(get_character_storage_service)
):
    """Update a character's prompt."""
    try:
        success = storage.update_prompt(character_id, request.prompt)
        if not success:
            raise HTTPException(status_code=404, detail=f"Character not found: {character_id}")

        character = storage.get_character(character_id)
        return CharacterResponse(character=character)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update character: {str(e)}")
