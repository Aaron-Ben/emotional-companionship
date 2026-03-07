"""Character data models - Simplified for file system based storage.

Characters are stored as:
- data/characters/{uuid}/prompt.md - Character system prompt
- data/characters/{uuid}/topics/ - Conversation topics
- data/characters/{uuid}/.character_meta.json - Metadata (name, created_at, updated_at)
- data/daily/{name}/ - Diary files (global directory organized by name)

Each character has:
- character_id: UUID4 (also used as directory name)
- name: Display name (from .character_meta.json)
- created_at: Creation timestamp (from .character_meta.json)
- updated_at: Last update timestamp (from .character_meta.json)
"""

from pydantic import BaseModel, Field


class Character(BaseModel):
    """User-created character stored in file system."""
    character_id: str = Field(..., description="UUID4 of the character")
    name: str = Field(..., description="Character display name")
    created_at: str = Field(..., description="ISO format creation timestamp")
    updated_at: str = Field(..., description="ISO format last update timestamp")


# Backward compatibility alias
UserCharacter = Character


# Empty class for backward compatibility - user preferences are not currently implemented
class UserCharacterPreference(BaseModel):
    """Placeholder for user character preferences (not currently implemented)."""
    pass
