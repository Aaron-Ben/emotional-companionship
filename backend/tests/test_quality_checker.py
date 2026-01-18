"""Tests for DiaryQualityService."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from app.services.diary.quality import DiaryQualityService, QualityResult


class TestQualityResult:
    """Test QualityResult dataclass."""

    def test_quality_result_acceptable(self):
        """Test acceptable quality result."""
        result = QualityResult(is_acceptable=True)
        assert result.is_acceptable is True
        assert result.reason is None
        assert result.confidence == 1.0

    def test_quality_result_not_acceptable(self):
        """Test not acceptable quality result."""
        result = QualityResult(
            is_acceptable=False,
            reason="Content too short",
            confidence=0.9
        )
        assert result.is_acceptable is False
        assert result.reason == "Content too short"
        assert result.confidence == 0.9


class TestDiaryQualityService:
    """Test DiaryQualityService class."""

    def test_quality_checker_init(self):
        """Test quality checker initialization."""
        checker = DiaryQualityService()
        assert checker is not None

    def test_check_hollowness_good_content(self):
        """Test hollowness check passes for good content."""
        checker = DiaryQualityService()
        result = checker._check_hollowness(
            "今天学习了Python异步编程的原理，理解了协程的工作方式"
        )

        assert result.is_acceptable is True

    def test_check_hollowness_too_short(self):
        """Test hollowness check fails for too short content."""
        checker = DiaryQualityService()
        result = checker._check_hollowness("好的")

        assert result.is_acceptable is False
        assert "过短" in result.reason

    def test_check_hollowness_hollow_keywords(self):
        """Test hollowness check fails for hollow keyword content."""
        checker = DiaryQualityService()
        # Create content that's long enough but mostly hollow keywords
        # Use enough hollow keywords to trigger the 30% threshold
        hollow_content = ("好的好的好的嗯嗯知道了知道了收到收到呵呵呵呵哈哈嘻嘻嘻嘻" +
                         "真的好的收到收到嗯嗯好的好的" +
                         "好的好的好的嗯嗯知道了知道了收到收到呵呵呵呵哈哈嘻嘻嘻嘻" +
                         "真的好的收到收到嗯嗯好的好的")
        result = checker._check_hollowness(hollow_content)

        assert result.is_acceptable is False
        # Can fail on either hollow keywords or lack of substantive content
        assert "空洞" in result.reason or "缺少实质" in result.reason

    def test_check_hollowness_no_substantive_content(self):
        """Test hollowness check fails for non-substantive content."""
        checker = DiaryQualityService()
        # Create longer content without substantive patterns
        result = checker._check_hollowness("今天天气确实不错挺好的非常好很不错呀")

        # Should fail either on hollowness or lack of substantive content
        assert result.is_acceptable is False

    def test_check_duplicates_no_duplicates(self):
        """Test duplicate check passes when no duplicates."""
        checker = DiaryQualityService()
        result = checker._check_duplicates(
            "今天学习了Python编程",
            recent_diaries=["昨天学习了Java", "前天学习了C++"]
        )

        assert result.is_acceptable is True

    def test_check_duplicates_with_duplicates(self):
        """Test duplicate check fails with duplicate content."""
        checker = DiaryQualityService()
        result = checker._check_duplicates(
            "今天学习了Python编程的基础知识",
            recent_diaries=["今天学习了Python编程的基础知识", "昨天学习了Java"]
        )

        assert result.is_acceptable is False
        assert "重复" in result.reason

    def test_calculate_similarity_identical(self):
        """Test similarity calculation for identical texts."""
        checker = DiaryQualityService()
        similarity = checker._calculate_similarity(
            "Python编程",
            "Python编程"
        )

        assert similarity == 1.0

    def test_calculate_similarity_different(self):
        """Test similarity calculation for different texts."""
        checker = DiaryQualityService()
        similarity = checker._calculate_similarity(
            "Python编程",
            "Java编程"
        )

        assert similarity < 1.0
        assert similarity > 0.0

    def test_check_quality_comprehensive(self):
        """Test comprehensive quality check."""
        checker = DiaryQualityService()
        result = checker.check_quality(
            diary_content="今天学习了Python异步编程，理解了event loop的工作原理",
            recent_diaries=["昨天学习了Java多线程"]
        )

        assert result.is_acceptable is True

    def test_check_quality_fails_hollowness(self):
        """Test comprehensive quality check fails on hollowness."""
        checker = DiaryQualityService()
        result = checker.check_quality(
            diary_content="好的嗯嗯",
            recent_diaries=[]
        )

        assert result.is_acceptable is False

    @patch('app.services.diary.quality.SessionLocal')
    def test_get_recent_diaries(self, mock_session_local):
        """Test getting recent diaries from database."""
        # Setup mock for database session
        mock_db = Mock()
        mock_diary = Mock()
        mock_diary.content = "Yesterday's diary content"

        # Setup the query chain
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_diary]

        mock_db.query.return_value = mock_query

        # Setup context manager mock
        mock_session_local.return_value = mock_db

        checker = DiaryQualityService()
        import asyncio

        async def run_test():
            diaries = await checker.get_recent_diaries(
                character_id="sister_001",
                user_id="user_default",
                limit=5
            )
            assert len(diaries) == 1
            assert diaries[0] == "Yesterday's diary content"

        asyncio.run(run_test())

    def test_duplicate_threshold(self):
        """Test that duplicate threshold is correctly applied."""
        checker = DiaryQualityService()

        # Similar content should trigger duplicate check (threshold 0.85)
        similar_content = "今天学习了Python编程的基础知识和核心概念"
        original = "今天学习了Python编程的基础知识和核心要点"

        result = checker._check_duplicates(
            similar_content,
            [original]
        )

        # Should fail due to high similarity
        assert result.is_acceptable is False
