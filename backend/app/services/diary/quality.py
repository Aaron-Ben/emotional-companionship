"""Diary quality checking service.

Simplified from quality_checker.py with unified quality checking.
"""

import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Optional

from app.models.database import SessionLocal, DiaryTable

logger = logging.getLogger(__name__)


@dataclass
class QualityResult:
    """Quality check result."""
    is_acceptable: bool
    reason: Optional[str] = None
    confidence: float = 1.0


class DiaryQualityService:
    """Diary content quality checker.

    Validates diary quality by filtering out:
    - Hollow/low-quality content
    - Duplicate entries
    - Content below minimum length
    """

    # Hollow content keywords
    HOLLOW_KEYWORDS = [
        "好的", "嗯", "知道了", "收到", "了解",
        "哈哈", "呵呵", "嘻嘻", "啦啦",
        "今天天气不错", "今天很好", "没什么特别的"
    ]

    # Minimum content length (characters)
    MIN_CONTENT_LENGTH = 20

    # Duplicate similarity threshold
    DUPLICATE_SIMILARITY_THRESHOLD = 0.85

    def check_quality(
        self,
        diary_content: str,
        recent_diaries: Optional[List[str]] = None
    ) -> QualityResult:
        """Check diary quality.

        Args:
            diary_content: Diary content to check
            recent_diaries: Recent diary contents for duplicate detection

        Returns:
            Quality check result
        """
        # Check hollow content
        hollow_result = self._check_hollowness(diary_content)
        if not hollow_result.is_acceptable:
            return hollow_result

        # Check duplicate content
        if recent_diaries:
            duplicate_result = self._check_duplicates(diary_content, recent_diaries)
            if not duplicate_result.is_acceptable:
                return duplicate_result

        return QualityResult(is_acceptable=True, confidence=1.0)

    def _check_hollowness(self, content: str) -> QualityResult:
        """Check for hollow/empty content.

        Args:
            content: Diary content

        Returns:
            Quality check result
        """
        # Check content length
        if len(content) < self.MIN_CONTENT_LENGTH:
            return QualityResult(
                is_acceptable=False,
                reason=f"内容过短（{len(content)}字符），最少需要{self.MIN_CONTENT_LENGTH}字符",
                confidence=0.9
            )

        # Check if mostly hollow keywords
        content_lower = content.lower()
        hollow_count = sum(1 for kw in self.HOLLOW_KEYWORDS if kw in content_lower)
        hollow_ratio = (hollow_count * len(self.HOLLOW_KEYWORDS[0])) / len(content)

        if hollow_ratio > 0.3:
            return QualityResult(
                is_acceptable=False,
                reason="内容空洞，缺少实质信息",
                confidence=0.8
            )

        # Check for substantive content
        substantive_patterns = [
            r"学到", r"了解", r"讨论", r"决定", r"计划",
            r"觉得", r"认为", r"感到", r"发现", r"意识到",
            r"今天", r"明天", r"昨天",
            r"因为", r"所以", r"但是",
        ]

        has_substantive = any(
            re.search(pattern, content_lower)
            for pattern in substantive_patterns
        )

        if not has_substantive:
            return QualityResult(
                is_acceptable=False,
                reason="缺少实质性内容或观点",
                confidence=0.7
            )

        return QualityResult(is_acceptable=True)

    def _check_duplicates(self, content: str, recent_diaries: List[str]) -> QualityResult:
        """Check for duplicate content.

        Args:
            content: Diary content to check
            recent_diaries: Recent diary contents

        Returns:
            Quality check result
        """
        for i, recent_diary in enumerate(recent_diaries):
            similarity = self._calculate_similarity(content, recent_diary)

            if similarity >= self.DUPLICATE_SIMILARITY_THRESHOLD:
                return QualityResult(
                    is_acceptable=False,
                    reason=f"与最近的日记（第{i+1}篇）重复度过高（{similarity:.1%}）",
                    confidence=similarity
                )

        return QualityResult(is_acceptable=True)

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using SequenceMatcher.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1)
        """
        return SequenceMatcher(None, text1, text2).ratio()

    async def get_recent_diaries(
        self,
        character_id: str,
        user_id: str,
        limit: int = 5
    ) -> List[str]:
        """Get recent diary contents for quality checking.

        Args:
            character_id: Character ID
            user_id: User ID
            limit: Number of diaries to retrieve

        Returns:
            List of recent diary contents
        """
        db = SessionLocal()
        try:
            diaries = db.query(DiaryTable).filter(
                DiaryTable.character_id == character_id,
                DiaryTable.user_id == user_id
            ).order_by(
                DiaryTable.created_at.desc()
            ).limit(limit).all()

            return [diary.content for diary in diaries]
        finally:
            db.close()
