#!/usr/bin/env python3
"""
Migration script to convert from YAML-based character system to file system based system.

This script:
1. Extracts system_prompt.base from sister.yaml and creates prompt.md
2. Moves data/diary/sister_001/* to data/characters/{uuid}/daily/
3. Moves data/chat/user_default/{uuid}/topics/ to data/characters/{uuid}/chat/topics/

Since character_id IS now the UUID, we create a new UUID for the sister character.
"""

import os
import shutil
import uuid
import yaml
from pathlib import Path


# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
OLD_DIARY_DIR = PROJECT_ROOT / "data" / "diary"
OLD_CHAT_DIR = PROJECT_ROOT / "data" / "chat"
NEW_CHARACTERS_DIR = PROJECT_ROOT / "data" / "characters"
OLD_CHARACTERS_YAML = PROJECT_ROOT / "backend" / "app" / "characters" / "sister.yaml"


def load_yaml_character(yaml_path: Path) -> dict:
    """Load character YAML file."""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def create_character_directory(character_uuid: str, character_data: dict) -> Path:
    """Create character directory with prompt.md."""
    character_dir = NEW_CHARACTERS_DIR / character_uuid
    character_dir.mkdir(parents=True, exist_ok=True)

    # Create prompt.md from system_prompt.base
    # Add name as heading
    name = character_data.get('name', 'Character')
    prompt_content = f"# {name}\n\n" + character_data.get('system_prompt', {}).get('base', '')

    prompt_file = character_dir / "prompt.md"
    prompt_file.write_text(prompt_content, encoding='utf-8')
    print(f"Created: {prompt_file}")

    # Create subdirectories
    (character_dir / "daily").mkdir(exist_ok=True)
    (character_dir / "chat" / "topics").mkdir(parents=True, exist_ok=True)

    return character_dir


def migrate_diary_files(character_uuid: str, character_dir: Path):
    """Migrate diary files from old location to new structure."""
    old_diary_dir = OLD_DIARY_DIR / "sister_001"
    new_daily_dir = character_dir / "daily"

    if not old_diary_dir.exists():
        print(f"No diary files found for sister_001")
        return

    for diary_file in old_diary_dir.glob("*.txt"):
        dest_file = new_daily_dir / diary_file.name
        shutil.copy2(diary_file, dest_file)
        print(f"Copied diary: {diary_file} -> {dest_file}")


def migrate_chat_topics(old_uuid: str, new_uuid: str, character_dir: Path):
    """Migrate chat topics from old location to new structure."""
    old_user_dir = OLD_CHAT_DIR / "user_default"
    old_topics_dir = old_user_dir / old_uuid / "topics"
    new_chat_dir = character_dir / "chat"

    if not old_topics_dir.exists():
        print(f"No chat topics found for {old_uuid}")
        return

    new_topics_dir = new_chat_dir / "topics"

    for topic_dir in old_topics_dir.iterdir():
        if topic_dir.is_dir():
            dest_dir = new_topics_dir / topic_dir.name
            if dest_dir.exists():
                continue
            shutil.copytree(topic_dir, dest_dir)
            print(f"Copied topic: {topic_dir} -> {dest_dir}")


def migrate():
    """Main migration function."""
    print("=" * 60)
    print("Character Migration: YAML -> File System")
    print("=" * 60)

    if not OLD_CHARACTERS_YAML.exists():
        print(f"Error: Character YAML not found at {OLD_CHARACTERS_YAML}")
        return

    character_data = load_yaml_character(OLD_CHARACTERS_YAML)
    print(f"\nMigrating character: sister_001")
    print(f"Name: {character_data.get('name')}")

    # Get old UUID from mappings if exists
    old_uuid = None
    mappings_file = OLD_CHAT_DIR / ".mappings.json"
    if mappings_file.exists():
        try:
            import json
            with open(mappings_file, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
                old_uuid = mappings.get("characters", {}).get("sister_001")
        except:
            pass

    if old_uuid:
        print(f"Old UUID: {old_uuid}")
    else:
        print("No old UUID found, will skip chat migration")

    # Create new UUID as character_id
    new_uuid = str(uuid.uuid4())
    print(f"New UUID (character_id): {new_uuid}")

    # Create character directory structure
    print("\n1. Creating character directory...")
    character_dir = create_character_directory(new_uuid, character_data)
    print(f"   Character dir: {character_dir}")

    # Migrate diary files
    print("\n2. Migrating diary files...")
    migrate_diary_files(new_uuid, character_dir)

    # Migrate chat topics if old UUID exists
    if old_uuid:
        print("\n3. Migrating chat topics...")
        migrate_chat_topics(old_uuid, new_uuid, character_dir)

    # Save new UUID to localStorage info
    print("\n" + "=" * 60)
    print("Migration completed successfully!")
    print(f"Character data migrated to: {character_dir}")
    print(f"\nNew character_id (UUID): {new_uuid}")
    print("\nIMPORTANT: Update your localStorage to use the new character_id:")
    print(f"  localStorage.setItem('selectedCharacterId', '{new_uuid}')")
    print("=" * 60)
    print("\nNote: Old files remain in place. You may remove them after verification:")
    print(f"  - Old diary: {OLD_DIARY_DIR / 'sister_001'}")
    if old_uuid:
        print(f"  - Old chat: {OLD_CHAT_DIR / 'user_default' / old_uuid}")


if __name__ == "__main__":
    migrate()
