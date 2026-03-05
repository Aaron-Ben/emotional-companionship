"""Character service for loading character prompts from file system."""

from typing import Optional
from pathlib import Path

from app.services.character_storage_service import CharacterStorageService


class CharacterService:
    """
    Simplified character service for loading character prompts.

    All characters are stored as markdown files in data/characters/{uuid}/prompt.md
    where {uuid} IS the character_id - no separate mapping needed.
    """

    def __init__(self):
        self._storage_service: Optional[CharacterStorageService] = None

    def _get_storage_service(self) -> CharacterStorageService:
        """Get or create the character storage service."""
        if self._storage_service is None:
            self._storage_service = CharacterStorageService()
        return self._storage_service

    def get_system_prompt(self, character_id: str) -> Optional[str]:
        """Get the system prompt for a character."""
        storage = self._get_storage_service()
        prompt = storage.get_prompt(character_id)
        if prompt:
            return self._get_datetime_context() + "\n\n" + prompt
        return None

    def _get_datetime_context(self) -> str:
        """Get current date and time information for the character."""
        from datetime import datetime

        now = datetime.now()
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']

        hour = now.hour
        if 5 <= hour < 12:
            period = "上午"
        elif 12 <= hour < 14:
            period = "中午"
        elif 14 <= hour < 18:
            period = "下午"
        elif 18 <= hour < 22:
            period = "晚上"
        else:
            period = "深夜"

        return f"""
## 当前时间信息

今天是 {now.year}年{now.month}月{now.day}日，{weekdays[now.weekday()]}。
现在是 {period} {now.hour}点{now.minute}分。

请在对话中自然地运用这个时间信息。
"""
