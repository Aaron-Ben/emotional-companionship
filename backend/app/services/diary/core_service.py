"""Core diary service for generating and managing diary entries."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.models.database import SessionLocal, DiaryTable
from app.services.llms.base import LLMBase
from app.services.diary.tag_service import DiaryTagService

logger = logging.getLogger(__name__)


class DiaryCoreService:
    """Core diary service for unified diary generation and storage.

    Simplified from the old service.py by:
    - Single generation method (extract_diary_from_conversation)
    - Single storage (SQLite only, no file system)
    - Modular prompt loading from external files
    """

    def __init__(self):
        """Initialize the diary core service."""
        self.prompts_dir = Path(__file__).parent / "prompts"

    def _load_prompt(self, prompt_name: str) -> str:
        """Load prompt from file.

        Args:
            prompt_name: Name of the prompt file (e.g., 'diary_generation.txt')

        Returns:
            Prompt content as string
        """
        prompt_path = self.prompts_dir / prompt_name
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_path}")
            raise

    def _format_conversation(self, messages: List[Dict]) -> str:
        """Format conversation messages for diary extraction.

        Args:
            messages: List of conversation messages with 'role' and 'content'

        Returns:
            Formatted conversation text
        """
        lines = []
        for msg in messages:
            role = "哥哥" if msg["role"] == "user" else "我"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def _build_diary_prompt(self, conversation_text: str) -> str:
        """Build diary generation prompt from template.

        Args:
            conversation_text: Formatted conversation text

        Returns:
            Complete prompt for LLM
        """
        prompt_template = self._load_prompt("diary_generation.txt")
        return prompt_template.format(conversation_text=conversation_text)

    def _parse_diary_response(self, response: str) -> Optional[Dict[str, any]]:
        """Parse LLM response to extract category and diary content.

        Args:
            response: LLM response text

        Returns:
            Dict with 'category' and 'content' if worth recording, None otherwise
        """
        response = response.strip()

        # Check if not worth recording
        if "【不值得记录】" in response:
            return None

        # Extract category from the first line
        lines = response.split("\n", 1)
        first_line = lines[0].strip()

        if first_line.startswith("分类："):
            category = first_line.split("：", 1)[1].strip()
            diary_content = lines[1].strip() if len(lines) > 1 else ""
        else:
            # No category specified, use default
            category = "topic"
            diary_content = response

        return {"category": category, "content": diary_content}

    async def generate_from_conversation(
        self,
        llm: LLMBase,
        character_id: str,
        user_id: str,
        conversation_messages: List[Dict],
    ) -> Optional['DiaryEntry']:
        """Generate diary from actual conversation.

        This method separates assessment, generation, and tagging into distinct steps:
        1. LLM judges if conversation is worth recording and generates diary with category
        2. Separate DiaryTagService call for high-density tag generation
        3. Tag line appended to diary content: "Tag: tag1, tag2, tag3"

        Args:
            llm: LLM service instance
            character_id: Character ID
            user_id: User ID
            conversation_messages: Complete conversation history

        Returns:
            Generated diary entry, or None if not worth recording
        """
        # Format conversation
        conversation_text = self._format_conversation(conversation_messages)

        # Build and send diary generation prompt
        prompt = self._build_diary_prompt(conversation_text)
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "判断是否值得记录并写日记～"}
        ]

        response = llm.generate_response(messages)

        # Parse response
        parsed = self._parse_diary_response(response)
        if parsed is None:
            logger.info("Conversation not worth recording diary")
            return None

        diary_content = parsed["content"]
        category = parsed["category"]

        # Generate tags using separate DiaryTagService
        tag_service = DiaryTagService()
        tags = tag_service.generate_tags(diary_content, category, llm)

        # Append tag line to content
        if tags:
            tag_line = f"\n\nTag: {', '.join(tags)}"
            diary_content_with_tags = diary_content + tag_line
        else:
            # Fallback to category if no tags generated
            tags = [category]
            diary_content_with_tags = f"{diary_content}\n\nTag: {category}"

        # Extract emotions
        emotions = self._extract_emotions(diary_content)

        # Create diary entry
        from app.models.diary import DiaryEntry
        diary_entry = DiaryEntry(
            id=self._generate_diary_id(character_id, user_id),
            character_id=character_id,
            user_id=user_id,
            date=datetime.now().strftime("%Y-%m-%d"),
            content=diary_content_with_tags,
            category=category,
            emotions=emotions,
            tags=tags
        )

        # Save to SQLite
        await self._save_diary(diary_entry)
        return diary_entry

    async def _save_diary(self, diary_entry: 'DiaryEntry') -> None:
        """Save diary to SQLite database.

        Args:
            diary_entry: Diary entry to save
        """
        db = SessionLocal()
        try:
            db_diary = DiaryTable(
                id=diary_entry.id,
                character_id=diary_entry.character_id,
                user_id=diary_entry.user_id,
                date=diary_entry.date,
                content=diary_entry.content,
                category=diary_entry.category,
                emotions=diary_entry.emotions,
                tags=diary_entry.tags,
                created_at=diary_entry.created_at,
                updated_at=diary_entry.updated_at
            )
            db.add(db_diary)
            db.commit()
            logger.info(f"Diary saved: {diary_entry.id}")
        finally:
            db.close()

    def _generate_diary_id(self, character_id: str, user_id: str) -> str:
        """Generate unique diary ID.

        Args:
            character_id: Character ID
            user_id: User ID

        Returns:
            Unique diary ID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"diary_{character_id}_{user_id}_{timestamp}"

    def _extract_emotions(self, content: str) -> List[str]:
        """Extract emotion tags from diary content.

        Args:
            content: Diary content

        Returns:
            List of emotion labels
        """
        emotions = []
        emotion_keywords = {
            "开心": ["开心", "高兴", "快乐", "幸福", "兴奋"],
            "难过": ["难过", "伤心", "痛苦", "郁闷", "悲伤"],
            "生气": ["生气", "愤怒", "气死", "讨厌"],
            "担心": ["担心", "忧虑", "紧张", "害怕"],
            "温暖": ["温暖", "感动", "幸福", "甜蜜"],
            "期待": ["期待", "盼望", "希望", "向往"]
        }

        content_lower = content.lower()
        for emotion, keywords in emotion_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                if emotion not in emotions:
                    emotions.append(emotion)

        return emotions if emotions else ["平静"]

    async def get_relevant_diaries(
        self,
        character_id: str,
        user_id: str,
        current_message: str,
        limit: int = 5
    ) -> List['DiaryEntry']:
        """Get diaries relevant to current message.

        Args:
            character_id: Character ID
            user_id: User ID
            current_message: Current user message
            limit: Maximum number of diaries to return

        Returns:
            List of relevant diary entries
        """
        db = SessionLocal()
        try:
            diaries = db.query(DiaryTable).filter(
                DiaryTable.character_id == character_id,
                DiaryTable.user_id == user_id
            ).order_by(DiaryTable.created_at.desc()).limit(20).all()

            from app.models.diary import DiaryEntry
            relevant_diaries = []
            for db_diary in diaries:
                diary_entry = DiaryEntry(
                    id=db_diary.id,
                    character_id=db_diary.character_id,
                    user_id=db_diary.user_id,
                    date=db_diary.date,
                    content=db_diary.content,
                    category=db_diary.category,
                    emotions=db_diary.emotions,
                    tags=db_diary.tags,
                    created_at=db_diary.created_at,
                    updated_at=db_diary.updated_at
                )

                if self._is_relevant(diary_entry, current_message):
                    relevant_diaries.append(diary_entry)
                    if len(relevant_diaries) >= limit:
                        break

            return relevant_diaries
        finally:
            db.close()

    def _is_relevant(self, diary: 'DiaryEntry', message: str) -> bool:
        """Check if diary is relevant to current message.

        Args:
            diary: Diary entry
            message: Current message

        Returns:
            True if relevant
        """
        message_lower = message.lower()

        # Check tag match
        for tag in diary.tags:
            if tag.lower() in message_lower:
                return True

        # Check emotion match
        for emotion in diary.emotions:
            if emotion.lower() in message_lower:
                return True

        # Check content keywords
        keywords = ["哥哥", "今天", "昨天", "开心", "难过"]
        for keyword in keywords:
            if keyword in diary.content and keyword in message_lower:
                return True

        return False
