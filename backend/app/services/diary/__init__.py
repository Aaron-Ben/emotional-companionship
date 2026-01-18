"""Diary-related services for emotional companionship system.

Simplified diary system with:
- Unified core service for diary generation
- Modular prompt-based system
- SQLite-only storage (no file system)
- AI-powered quality checking and tag generation
"""

from app.services.diary.core_service import DiaryCoreService
from app.services.diary.assessor import DiaryAssessmentService
from app.services.diary.tag_service import DiaryTagService
from app.services.diary.quality import DiaryQualityService, QualityResult

__all__ = [
    "DiaryCoreService",
    "DiaryAssessmentService",
    "DiaryTagService",
    "DiaryQualityService",
    "QualityResult",
]
