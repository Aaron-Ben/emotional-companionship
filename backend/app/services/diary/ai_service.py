"""AI Diary Service for creating and updating diaries via AI.

Similar to VCPToolBox DailyNote plugin functionality:
- create: AI creates diary with tag processing
- update: AI updates diary by finding and replacing content
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.models.database import SessionLocal, DiaryTable
from app.models.diary import DiaryEntry
from app.services.diary.core_service import DiaryCoreService

logger = logging.getLogger(__name__)


class AIDiaryService:
    """Service for AI-based diary creation and updates."""

    TAG_PATTERN = re.compile(r'^Tag:\s*(.+)$', re.MULTILINE | re.IGNORECASE)

    def __init__(self):
        """Initialize the AI diary service."""
        self.core_service = DiaryCoreService()

    def _detect_and_extract_tag(self, content: str) -> Tuple[str, Optional[str]]:
        """Detect and extract tag from content.

        Args:
            content: Diary content that may contain a Tag line at the end

        Returns:
            Tuple of (content_without_tag, extracted_tag_or_none)
        """
        lines = content.split('\n')

        # Check if last line is a tag line
        if lines:
            last_line = lines[-1].strip()
            match = self.TAG_PATTERN.match(last_line)
            if match:
                tag_content = match.group(1).strip()
                content_without_tag = '\n'.join(lines[:-1]).rstrip()
                logger.info(f"Tag detected in content: {tag_content}")
                return content_without_tag, tag_content

        return content, None

    def _parse_tag_string(self, tag_string: str) -> List[str]:
        """Parse tag string into list of tags.

        Supports various separators: comma, Chinese comma, enum comma

        Args:
            tag_string: Tag string like "tag1, tag2, tag3"

        Returns:
            List of normalized tags
        """
        # Replace various Chinese separators with comma
        normalized = tag_string.replace('，', ',').replace('、', ',').replace(';', ',')

        # Split by comma and clean up
        tags = [tag.strip() for tag in normalized.split(',') if tag.strip()]

        return tags

    async def create_diary(
        self,
        character_id: str,
        user_id: str,
        date: str,
        content: str,
        category: str = "topic",
        tag: Optional[str] = None
    ) -> DiaryEntry:
        """Create a new diary entry.

        Args:
            character_id: Character ID
            user_id: User ID
            date: Diary date (YYYY-MM-DD)
            content: Diary content (may contain Tag line at end)
            category: Diary category
            tag: Optional independent tag field (overrides content tag)

        Returns:
            Created diary entry

        Raises:
            ValueError: If date format is invalid or tag is missing
        """
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {date}. Expected YYYY-MM-DD")

        # Process tags: external tag takes priority over content tag
        tags: List[str] = []
        final_content = content

        if tag and tag.strip():
            # Use external tag
            tags = self._parse_tag_string(tag.strip())
            # Remove any existing Tag line from content
            final_content, _ = self._detect_and_extract_tag(content)
            logger.info(f"Using external tag: {tags}")
        else:
            # Try to extract tag from content
            final_content, extracted_tag = self._detect_and_extract_tag(content)
            if extracted_tag:
                tags = self._parse_tag_string(extracted_tag)
            else:
                # No tag found, this is required
                raise ValueError(
                    "Tag is missing. Please provide a 'tag' parameter or add a 'Tag:' line at the end of the 'content'."
                )

        # Append tag line to content for storage
        tag_line = f"\n\nTag: {', '.join(tags)}"
        content_with_tag = final_content.rstrip() + tag_line

        # Create diary entry
        diary_id = self._generate_diary_id(character_id, user_id)
        now = datetime.now()

        diary_entry = DiaryEntry(
            id=diary_id,
            character_id=character_id,
            user_id=user_id,
            date=date,
            content=content_with_tag,
            category=category,
            tags=tags,
            created_at=now,
            updated_at=None
        )

        # Save to database
        await self._save_diary(diary_entry)

        logger.info(f"AI created diary: {diary_id} for character {character_id}")
        return diary_entry

    async def update_diary(
        self,
        target: str,
        replace: str,
        user_id: str,
        character_id: Optional[str] = None
    ) -> Dict[str, any]:
        """Update diary by finding and replacing content.

        Args:
            target: Content to search for (must be >= 15 characters)
            replace: Replacement content
            user_id: User ID
            character_id: Optional character ID to narrow search

        Returns:
            Dict with status and message
        """
        if len(target) < 15:
            return {
                "status": "error",
                "message": f"Security check failed: 'target' must be at least 15 characters long. Provided length: {len(target)}"
            }

        db = SessionLocal()
        try:
            # Build query
            query = db.query(DiaryTable).filter(DiaryTable.user_id == user_id)

            if character_id:
                query = query.filter(DiaryTable.character_id == character_id)

            # Get diaries ordered by created_at desc (most recent first)
            diaries = query.order_by(DiaryTable.created_at.desc()).all()

            logger.info(f"Searching for target in {len(diaries)} diaries")

            for db_diary in diaries:
                content = db_diary.content

                # Check if target exists in content
                if target in content:
                    # Replace the content
                    new_content = content.replace(target, replace, 1)  # Replace first occurrence only

                    # Update database
                    db_diary.content = new_content
                    db_diary.updated_at = datetime.now()

                    db.commit()
                    db.refresh(db_diary)

                    logger.info(f"AI updated diary: {db_diary.id}")

                    return {
                        "status": "success",
                        "message": f"Successfully edited diary file: {db_diary.id}",
                        "diary_id": db_diary.id
                    }

            # No match found
            char_msg = f" for character '{character_id}'" if character_id else ""
            return {
                "status": "error",
                "message": f"Target content not found in any diary files{char_msg}."
            }

        finally:
            db.close()

    async def _save_diary(self, diary_entry: DiaryEntry) -> None:
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[-19:]  # Include microseconds for uniqueness
        return f"diary_{character_id}_{user_id}_{timestamp}"
