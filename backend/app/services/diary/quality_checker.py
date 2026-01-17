"""Diary content quality checking service."""

import logging
from dataclasses import dataclass
from typing import List, Optional
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from app.models.database import SessionLocal, DiaryTable

logger = logging.getLogger(__name__)


@dataclass
class QualityResult:
    """质量检查结果"""
    is_acceptable: bool
    reason: Optional[str] = None
    confidence: float = 1.0  # 0-1之间的置信度


class DiaryQualityChecker:
    """日记内容质量检查器

    检查日记质量，过滤掉重复、空洞和包含幻觉的日记。
    """

    # 空洞内容的关键词（无实质信息）
    HOLLOW_KEYWORDS = [
        "好的", "嗯", "知道了", "收到", "了解",
        "哈哈", "呵呵", "嘻嘻", "啦啦",
        "今天天气不错", "今天很好", "没什么特别的"
    ]

    # 最小内容长度（字符数）
    MIN_CONTENT_LENGTH = 20

    # 重复相似度阈值
    DUPLICATE_SIMILARITY_THRESHOLD = 0.85

    def check_diary_quality(
        self,
        diary_content: str,
        recent_diaries: Optional[List[str]] = None
    ) -> QualityResult:
        """
        检查日记质量

        Args:
            diary_content: 待检查的日记内容
            recent_diaries: 最近的日记内容列表（用于重复检测）

        Returns:
            质量检查结果
        """
        # 1. 检查空洞内容
        hollow_result = self._check_hollowness(diary_content)
        if not hollow_result.is_acceptable:
            return hollow_result

        # 2. 检查重复内容
        if recent_diaries:
            duplicate_result = self._check_duplicates(diary_content, recent_diaries)
            if not duplicate_result.is_acceptable:
                return duplicate_result

        # 通过所有检查
        return QualityResult(is_acceptable=True, confidence=1.0)

    def _check_hollowness(self, content: str) -> QualityResult:
        """检查空洞内容（无实质信息）

        Args:
            content: 日记内容

        Returns:
            质量检查结果
        """
        # 检查内容长度
        if len(content) < self.MIN_CONTENT_LENGTH:
            return QualityResult(
                is_acceptable=False,
                reason=f"内容过短（{len(content)}字符），最少需要{self.MIN_CONTENT_LENGTH}字符",
                confidence=0.9
            )

        # 检查是否主要由空洞关键词组成
        content_lower = content.lower()
        hollow_count = sum(1 for kw in self.HOLLOW_KEYWORDS if kw in content_lower)
        total_chars = len(content)

        # 如果超过30%的内容是空洞关键词，判定为空洞
        hollow_ratio = (hollow_count * len(self.HOLLOW_KEYWORDS[0])) / total_chars
        if hollow_ratio > 0.3:
            return QualityResult(
                is_acceptable=False,
                reason="内容空洞，缺少实质信息",
                confidence=0.8
            )

        # 检查是否缺少实质内容（关键词检测）
        substantive_patterns = [
            r"学到", r"了解", r"讨论", r"决定", r"计划",
            r"觉得", r"认为", r"感到", r"发现", r"意识到",
            r"今天", r"明天", r"昨天",  # 时间词
            r"因为", r"所以", r"但是",  # 逻辑词
        ]

        import re
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
        """检查重复内容

        Args:
            content: 待检查的日记内容
            recent_diaries: 最近的日记内容列表

        Returns:
            质量检查结果
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
        """计算两个文本的相似度

        使用SequenceMatcher计算序列相似度

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            相似度（0-1之间）
        """
        return SequenceMatcher(None, text1, text2).ratio()

    async def get_recent_diaries(
        self,
        character_id: str,
        user_id: str,
        limit: int = 5
    ) -> List[str]:
        """
        获取最近的日记内容（用于质量检查）

        Args:
            character_id: 角色ID
            user_id: 用户ID
            limit: 获取数量

        Returns:
            最近日记的内容列表
        """
        db: Session = SessionLocal()
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
