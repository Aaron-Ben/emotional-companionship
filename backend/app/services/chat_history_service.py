"""Chat history service for file-based topic and message management."""

import os
import json
import uuid
import time
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from app.models.chat import ChatMessage, ChatTopic, ChatHistory


logger = logging.getLogger(__name__)


# Default paths
CHAT_DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "chat"
MAPPINGS_FILE = CHAT_DATA_DIR / ".mappings.json"
DEFAULT_TOPIC_NAME = "default"


class CharacterMappingService:
    """Service for managing character_id <-> UUID mappings."""

    def __init__(self, mappings_file: Optional[Path] = None):
        """Initialize the mapping service."""
        self.mappings_file = mappings_file or MAPPINGS_FILE
        self._mappings: Dict[str, str] = {}
        self._reverse_mappings: Dict[str, str] = {}
        self._load_mappings()

    def _load_mappings(self):
        """Load mappings from file."""
        try:
            if self.mappings_file.exists():
                with open(self.mappings_file, 'r', encoding='utf-8') as f:
                    self._mappings = json.load(f)
                    self._reverse_mappings = {v: k for k, v in self._mappings.get("characters", {}).items()}
                logger.info(f"Loaded {len(self._mappings.get('characters', {}))} character mappings")
            else:
                self._mappings = {"characters": {}}
                self._reverse_mappings = {}
                self._save_mappings()
        except Exception as e:
            logger.error(f"Error loading mappings: {e}")
            self._mappings = {"characters": {}}
            self._reverse_mappings = {}

    def _save_mappings(self):
        """Save mappings to file."""
        try:
            self.mappings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.mappings_file, 'w', encoding='utf-8') as f:
                json.dump(self._mappings, f, ensure_ascii=False, indent=2)
            logger.info("Saved character mappings")
        except Exception as e:
            logger.error(f"Error saving mappings: {e}")

    def get_or_create_mapping(self, character_id: str) -> str:
        """Get existing UUID or create new mapping for character_id."""
        # Check if mapping exists
        if character_id in self._mappings.get("characters", {}):
            return self._mappings["characters"][character_id]

        # Create new UUID mapping
        character_uuid = str(uuid.uuid4())
        self._mappings.setdefault("characters", {})[character_id] = character_uuid
        self._reverse_mappings[character_uuid] = character_id
        self._save_mappings()

        logger.info(f"Created new UUID mapping: {character_id} -> {character_uuid}")
        return character_uuid

    def get_character_uuid(self, character_id: str) -> Optional[str]:
        """Get UUID for character_id."""
        return self._mappings.get("characters", {}).get(character_id)

    def get_character_id(self, character_uuid: str) -> Optional[str]:
        """Get character_id from UUID."""
        return self._reverse_mappings.get(character_uuid)


class ChatHistoryService:
    """Service for managing chat history using file system storage."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize the chat history service."""
        self.data_dir = data_dir or CHAT_DATA_DIR
        self.mapping_service = CharacterMappingService()
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_user_dir(self, user_id: str) -> Path:
        """Get user directory path."""
        return self.data_dir / user_id

    def _get_character_dir(self, user_id: str, character_uuid: str) -> Path:
        """Get character directory path."""
        return self._get_user_dir(user_id) / character_uuid

    def _get_topics_dir(self, user_id: str, character_uuid: str) -> Path:
        """Get topics directory path."""
        return self._get_character_dir(user_id, character_uuid) / "topics"

    def _get_topic_dir(self, user_id: str, character_uuid: str, topic_id: int) -> Path:
        """Get specific topic directory path."""
        return self._get_topics_dir(user_id, character_uuid) / str(topic_id)

    def _get_history_file(self, user_id: str, character_uuid: str, topic_id: int) -> Path:
        """Get history.json file path for a topic."""
        return self._get_topic_dir(user_id, character_uuid, topic_id) / "history.json"

    def _ensure_topic_dirs(self, user_id: str, character_uuid: str):
        """Ensure topics directory exists."""
        topics_dir = self._get_topics_dir(user_id, character_uuid)
        topics_dir.mkdir(parents=True, exist_ok=True)

    def _read_history(self, history_file: Path) -> List[ChatMessage]:
        """Read history from file."""
        try:
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Handle both array format and object format with "messages" key
                    if isinstance(data, list):
                        return [ChatMessage(**msg) for msg in data]
                    elif isinstance(data, dict) and "messages" in data:
                        return [ChatMessage(**msg) for msg in data["messages"]]
            return []
        except Exception as e:
            logger.error(f"Error reading history from {history_file}: {e}")
            return []

    def _write_history(self, history_file: Path, messages: List[ChatMessage]):
        """Write history to file with atomic write."""
        try:
            # Ensure parent directory exists
            history_file.parent.mkdir(parents=True, exist_ok=True)

            # Write to temporary file first
            temp_file = history_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                data = [msg.model_dump() for msg in messages]
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Atomic rename
            temp_file.replace(history_file)

            logger.debug(f"Saved {len(messages)} messages to {history_file}")
        except Exception as e:
            logger.error(f"Error writing history to {history_file}: {e}")
            raise

    def create_topic(self, user_id: str, character_uuid: str) -> int:
        """
        Create a new topic.

        Args:
            user_id: User ID
            character_uuid: Character UUID

        Returns:
            topic_id: Unix timestamp (seconds)
        """
        # Use current timestamp as topic_id
        topic_id = int(time.time())

        # Ensure directories exist
        self._ensure_topic_dirs(user_id, character_uuid)

        # Create topic directory with empty history
        topic_dir = self._get_topic_dir(user_id, character_uuid, topic_id)
        topic_dir.mkdir(parents=True, exist_ok=True)

        # Create empty history file
        history_file = self._get_history_file(user_id, character_uuid, topic_id)
        self._write_history(history_file, [])

        logger.info(f"Created topic {topic_id} for user {user_id}, character {character_uuid}")
        return topic_id

    def delete_topic(self, user_id: str, topic_id: int, character_uuid: Optional[str] = None) -> bool:
        """
        Delete a topic.

        Args:
            user_id: User ID
            topic_id: Topic ID to delete
            character_uuid: Optional character UUID for validation

        Returns:
            bool: True if deleted successfully
        """
        try:
            # If character_uuid not provided, search for topic
            if character_uuid is None:
                character_uuid = self._find_character_for_topic(user_id, topic_id)
                if character_uuid is None:
                    logger.warning(f"Topic {topic_id} not found for user {user_id}")
                    return False

            topic_dir = self._get_topic_dir(user_id, character_uuid, topic_id)

            if topic_dir.exists():
                import shutil
                shutil.rmtree(topic_dir)
                logger.info(f"Deleted topic {topic_id} for user {user_id}, character {character_uuid}")
                return True
            else:
                logger.warning(f"Topic directory not found: {topic_dir}")
                return False
        except Exception as e:
            logger.error(f"Error deleting topic {topic_id}: {e}")
            return False

    def _find_character_for_topic(self, user_id: str, topic_id: int) -> Optional[str]:
        """Find which character a topic belongs to."""
        user_dir = self._get_user_dir(user_id)
        if not user_dir.exists():
            return None

        for character_dir in user_dir.iterdir():
            if not character_dir.is_dir():
                continue
            topics_dir = character_dir / "topics"
            if topics_dir.exists() and (topics_dir / str(topic_id)).exists():
                return character_dir.name
        return None

    def list_topics(self, user_id: str, character_uuid: Optional[str] = None) -> List[ChatTopic]:
        """
        List topics for a user.

        Args:
            user_id: User ID
            character_uuid: Optional character UUID to filter by

        Returns:
            List of ChatTopic objects sorted by updated_at (newest first)
        """
        topics = []
        user_dir = self._get_user_dir(user_id)

        if not user_dir.exists():
            return topics

        for character_dir in user_dir.iterdir():
            if not character_dir.is_dir():
                continue

            # Filter by character_uuid if provided
            if character_uuid and character_dir.name != character_uuid:
                continue

            topics_dir = character_dir / "topics"
            if not topics_dir.exists():
                continue

            for topic_dir in topics_dir.iterdir():
                if not topic_dir.is_dir():
                    continue

                try:
                    topic_id = int(topic_dir.name)
                    history_file = topic_dir / "history.json"

                    # Get timestamps from filesystem
                    stat = topic_dir.stat()
                    created_at = int(stat.st_ctime)
                    updated_at = int(stat.st_mtime)

                    # Get message count from file
                    message_count = 0
                    if history_file.exists():
                        messages = self._read_history(history_file)
                        message_count = len(messages)

                    topics.append(ChatTopic(
                        topic_id=topic_id,
                        character_uuid=character_dir.name,
                        created_at=created_at,
                        updated_at=updated_at,
                        message_count=message_count
                    ))
                except (ValueError, OSError) as e:
                    logger.warning(f"Error reading topic {topic_dir}: {e}")
                    continue

        # Sort by updated_at (newest first)
        topics.sort(key=lambda t: t.updated_at, reverse=True)
        return topics

    def get_topic_history(self, user_id: str, topic_id: int, character_uuid: Optional[str] = None) -> List[ChatMessage]:
        """
        Get chat history for a topic.

        Args:
            user_id: User ID
            topic_id: Topic ID
            character_uuid: Optional character UUID (required if not in default location)

        Returns:
            List of ChatMessage objects
        """
        # Find character UUID if not provided
        if character_uuid is None:
            character_uuid = self._find_character_for_topic(user_id, topic_id)
            if character_uuid is None:
                logger.warning(f"Topic {topic_id} not found for user {user_id}")
                return []

        history_file = self._get_history_file(user_id, character_uuid, topic_id)
        return self._read_history(history_file)

    def append_message(self, user_id: str, topic_id: int, role: str, content: str, character_uuid: Optional[str] = None) -> ChatMessage:
        """
        Append a message to a topic.

        Args:
            user_id: User ID
            topic_id: Topic ID
            role: Message role ('user' or 'assistant')
            content: Message content
            character_uuid: Optional character UUID

        Returns:
            The created ChatMessage
        """
        # Find character UUID if not provided
        if character_uuid is None:
            character_uuid = self._find_character_for_topic(user_id, topic_id)
            if character_uuid is None:
                raise ValueError(f"Topic {topic_id} not found for user {user_id}")

        # Create new message
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=int(time.time())
        )

        # Read existing messages
        history_file = self._get_history_file(user_id, character_uuid, topic_id)
        messages = self._read_history(history_file)

        # Append new message
        messages.append(message)

        # Write back to file
        self._write_history(history_file, messages)

        logger.debug(f"Appended message to topic {topic_id} for user {user_id}")
        return message

    def get_or_create_default_topic(self, user_id: str, character_uuid: str) -> int:
        """
        Get existing default topic or create a new one.

        The default topic is the most recently updated topic for the character.

        Args:
            user_id: User ID
            character_uuid: Character UUID

        Returns:
            topic_id: Topic ID
        """
        topics = self.list_topics(user_id, character_uuid)

        if topics:
            # Return the most recently updated topic
            return topics[0].topic_id
        else:
            # Create new topic
            return self.create_topic(user_id, character_uuid)

    def get_history_for_chat(self, user_id: str, topic_id: Optional[int], character_uuid: str) -> List[Dict[str, str]]:
        """
        Get chat history formatted for LLM consumption.

        Args:
            user_id: User ID
            topic_id: Topic ID (if None, uses default topic)
            character_uuid: Character UUID

        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        if topic_id is None:
            topic_id = self.get_or_create_default_topic(user_id, character_uuid)

        messages = self.get_topic_history(user_id, topic_id, character_uuid)
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
