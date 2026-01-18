"""Tests for DiaryTagService."""

import pytest
from unittest.mock import Mock, patch

from app.services.diary.tag_service import DiaryTagService


class TestDiaryTagService:
    """Test DiaryTagService class."""

    def test_tag_generator_init(self):
        """Test tag generator initialization."""
        generator = DiaryTagService()
        assert generator is not None

    def test_generate_tags_with_mock(self):
        """Test tag generation with mocked LLM."""
        # Setup mock - create a simple mock with generate_response method
        mock_llm = Mock()
        mock_llm.generate_response.return_value = "[[Tag: Python异步编程, FastAPI依赖注入, 装饰器模式]]"

        generator = DiaryTagService()
        tags = generator.generate_tags(
            diary_content="今天学习了Python异步编程和FastAPI框架",
            category="knowledge",
            llm=mock_llm
        )

        assert len(tags) == 3
        assert "Python异步编程" in tags
        assert "FastAPI依赖注入" in tags
        assert "装饰器模式" in tags

    def test_generate_tags_fallback_on_llm_error(self):
        """Test tag generation fallback when LLM fails."""
        # Setup mock to raise exception
        mock_llm = Mock()
        mock_llm.generate_response.side_effect = Exception("LLM error")

        generator = DiaryTagService()
        tags = generator.generate_tags(
            diary_content="学习内容",
            category="knowledge",
            llm=mock_llm
        )

        # Should fallback to simple category tag
        assert len(tags) == 1
        assert tags[0] == "knowledge"

    def test_parse_tags_with_valid_format(self):
        """Test parsing tags in valid [[Tag: ...]] format."""
        generator = DiaryTagService()

        response = "[[Tag: Python编程, 异步开发, FastAPI框架]]"
        tags = generator._parse_tags(response)

        assert len(tags) == 3
        assert "Python编程" in tags
        assert "异步开发" in tags
        assert "FastAPI框架" in tags

    def test_parse_tags_with_invalid_format_fallback(self):
        """Test parsing tags falls back to line-by-line extraction."""
        generator = DiaryTagService()

        response = """Python编程
异步开发
FastAPI框架"""
        tags = generator._parse_tags(response)

        assert len(tags) >= 1

    def test_parse_tags_limits_to_five(self):
        """Test that parsing limits to 5 tags."""
        generator = DiaryTagService()

        response = "[[Tag: 标签1, 标签2, 标签3, 标签4, 标签5, 标签6, 标签7, 标签8, 标签9, 标签10]]"
        tags = generator._parse_tags(response)

        assert len(tags) == 5

    @patch('app.services.diary.tag_service.LLMBase')
    def test_load_tag_prompt_knowledge_category(self, mock_llm_base):
        """Test prompt loading for knowledge category."""
        generator = DiaryTagService()
        # Test that we can load the prompt template
        prompt = generator._load_prompt()

        assert "高密度" in prompt
        assert "标签生成" in prompt

    @patch('app.services.diary.tag_service.LLMBase')
    def test_generate_tags_format(self, mock_llm_base):
        """Test that tag generation returns properly formatted tags."""
        generator = DiaryTagService()
        # Test tag format
        tags = generator._parse_tags("[[Tag: Python编程, 异步开发, FastAPI框架]]")

        assert len(tags) == 3
        assert "Python编程" in tags
