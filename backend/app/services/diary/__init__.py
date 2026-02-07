"""Diary-related services for emotional companionship system.

File-based diary system:
- Diaries stored as text files in organized folders
- Database tracks file metadata (path, checksum, mtime, size)
- Similar to VCPToolBox DailyNote plugin functionality
"""

from app.services.diary.file_service import DiaryFileService, get_diary_root, sanitize_path_component

__all__ = [
    "DiaryFileService",
    "get_diary_root",
    "sanitize_path_component",
]
