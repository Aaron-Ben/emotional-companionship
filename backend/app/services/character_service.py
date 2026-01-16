"""Character service for managing character templates and generating personalized system prompts."""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, List, Any

from app.models.character import (
    CharacterTemplate,
    UserCharacterPreference,
    CharacterType
)


class CharacterService:
    """
    Service for managing character templates and user preferences.
    Handles loading character templates and generating personalized system prompts.
    """

    def __init__(self, characters_dir: Optional[str] = None):
        """
        Initialize character service.

        Args:
            characters_dir: Directory containing character YAML files.
                          Defaults to app/resources/characters/
        """
        if characters_dir is None:
            # Default to app/resources/characters/
            current_dir = Path(__file__).parent.parent
            characters_dir = current_dir / "resources" / "characters"

        self.characters_dir = Path(characters_dir)
        self._templates: Dict[str, CharacterTemplate] = {}
        self._load_all_templates()

    def _load_all_templates(self):
        """Load all character templates from YAML files."""
        if not self.characters_dir.exists():
            self.characters_dir.mkdir(parents=True, exist_ok=True)
            return

        for yaml_file in self.characters_dir.glob("*.yaml"):
            try:
                template = self._load_template_from_file(yaml_file)
                self._templates[template.character_id] = template
            except Exception as e:
                print(f"Error loading character template from {yaml_file}: {e}")

    def _load_template_from_file(self, file_path: Path) -> CharacterTemplate:
        """
        Load a character template from a YAML file.

        Args:
            file_path: Path to the YAML file

        Returns:
            CharacterTemplate: Loaded character template

        Raises:
            ValueError: If file cannot be loaded or parsed
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return CharacterTemplate(**data)

    def get_character(self, character_id: str) -> Optional[CharacterTemplate]:
        """
        Get a character template by ID.

        Args:
            character_id: Unique character identifier

        Returns:
            CharacterTemplate if found, None otherwise
        """
        return self._templates.get(character_id)

    def list_characters(self, character_type: Optional[CharacterType] = None) -> List[CharacterTemplate]:
        """
        List all available character templates.

        Args:
            character_type: Optional filter by character type

        Returns:
            List of character templates
        """
        characters = list(self._templates.values())

        if character_type:
            characters = [c for c in characters if c.character_type == character_type]

        return characters

    def generate_system_prompt(
        self,
        character_id: str,
        user_preferences: Optional[UserCharacterPreference] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a personalized system prompt for a character.

        Args:
            character_id: Character to generate prompt for
            user_preferences: Optional user preferences for customization
            context: Optional context information (e.g., user mood, recent events)

        Returns:
            str: Complete system prompt with all customizations applied

        Raises:
            ValueError: If character_id not found
        """
        character = self.get_character(character_id)
        if not character:
            raise ValueError(f"Character not found: {character_id}")

        # Start with base system prompt
        system_prompt = character.system_prompt.base

        # Apply user customizations
        if user_preferences:
            system_prompt = self._apply_user_preferences(
                system_prompt,
                character,
                user_preferences
            )

        # Apply context-aware modifications
        if context:
            system_prompt = self._apply_context_modifications(
                system_prompt,
                character,
                context
            )

        return system_prompt

    def _apply_user_preferences(
        self,
        base_prompt: str,
        character: CharacterTemplate,
        preferences: UserCharacterPreference
    ) -> str:
        """
        Apply user preferences to customize the system prompt.

        Args:
            base_prompt: Base system prompt
            character: Character template
            preferences: User preferences

        Returns:
            str: Customized system prompt
        """
        customized_prompt = base_prompt
        nickname = preferences.nickname or character.base_nickname

        # Replace nickname variables
        customized_prompt = customized_prompt.replace("{{nickname}}", nickname)

        # Adjust speaking style based on style_level
        style_adjustment = self._get_style_adjustment(preferences.style_level)

        # Add style adjustment section
        if style_adjustment:
            style_section = f"\n\n## 本次对话的特殊指示\n{style_adjustment}\n"
            customized_prompt += style_section

        # Add custom instructions if provided
        if preferences.custom_instructions:
            customized_prompt += f"\n\n## 额外上下文\n{preferences.custom_instructions}\n"

        # Add relationship notes if available
        if preferences.relationship_notes:
            customized_prompt += f"\n\n## 关系上下文\n{preferences.relationship_notes}\n"

        return customized_prompt

    def _get_style_adjustment(self, style_level: float) -> str:
        """
        Get style adjustment instructions based on style_level.

        Args:
            style_level: Maturity level (0.7-1.3)
                        - < 1.0: More playful/childlike
                        - 1.0: Normal
                        - > 1.0: More mature

        Returns:
            str: Style adjustment instructions
        """
        if style_level < 0.9:
            return """
            在这次对话中，要格外顽皮和亲昵：
            - 使用更多的波浪号（～）和可爱的结尾
            - 保持句子相对简短和热情
            - 更强烈地表达情绪
            - 使用更多亲昵的称呼
            """
        elif style_level > 1.1:
            return """
            在这次对话中，要稍微成熟一些，但依然保持关心：
            - 减少波浪号和可爱结尾的使用
            - 给出更有深度、更成熟的回应
            - 展现更深的情感理解
            - 以更成熟的方式给予支持
            """
        else:
            return ""

    def _apply_context_modifications(
        self,
        base_prompt: str,
        character: CharacterTemplate,
        context: Dict[str, Any]
    ) -> str:
        """
        Apply context-aware modifications to the system prompt.

        Args:
            base_prompt: Current system prompt
            character: Character template
            context: Context information (user_mood, should_avoid_argument, etc.)

        Returns:
            str: Context-modified system prompt
        """
        modified_prompt = base_prompt
        context_instructions = []

        # Check if user is angry/distressed
        user_mood = context.get("user_mood")
        if user_mood and user_mood.get("primary_emotion") in ["angry", "frustrated", "very_sad"]:
            context_instructions.append("""
            ## 重要：用户需要额外支持

            用户现在很心烦。你应该：
            - 格外温柔和支持
            - 不要争辩或表达不同意
            - 将情感舒适放在首位
            - 展现共情和理解
            - 避免玩闹式的调侃或吃醋
            """)

        # Check if arguments should be avoided
        if context.get("should_avoid_argument", False):
            context_instructions.append("""
            ## 重要：避免冲突

            在这次对话中，避免任何分歧或争辩。
            即使你有不同意见，现在也请保留。
            优先考虑和谐与支持。
            """)

        # Add conversation starters if proactivity is needed
        if context.get("initiate_topic", False) and character.conversation_starters:
            starter = character.conversation_starters[0]
            context_instructions.append(f"""
            ## 建议的对话开场

            考虑以这样的话开头："{starter}"
            """)

        # Append all context instructions
        if context_instructions:
            modified_prompt += "\n\n" + "\n".join(context_instructions)

        return modified_prompt

    def get_conversation_starter(
        self,
        character_id: str,
        user_preferences: Optional[UserCharacterPreference] = None
    ) -> Optional[str]:
        """
        Get a conversation starter for a character.

        Args:
            character_id: Character to get starter for
            user_preferences: Optional user preferences

        Returns:
            str: Conversation starter or None
        """
        character = self.get_character(character_id)
        if not character or not character.conversation_starters:
            return None

        # For now, return the first starter
        # Could be enhanced to rotate based on time, history, etc.
        import random
        starter = random.choice(character.conversation_starters)

        # Replace nickname if user has custom preference
        if user_preferences and user_preferences.nickname:
            starter = starter.replace("哥哥", user_preferences.nickname)

        return starter
