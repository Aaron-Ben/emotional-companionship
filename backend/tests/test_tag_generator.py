"""Tests for DiaryTagGenerator."""

import pytest
from unittest.mock import Mock, patch

from app.services.diary.tag_generator import DiaryTagGenerator


class TestDiaryTagGenerator:
    """Test DiaryTagGenerator class."""

    def test_tag_generator_init(self):
        """Test tag generator initialization."""
        generator = DiaryTagGenerator()
        assert generator is not None

    def test_generate_tags_with_mock(self):
        """Test tag generation with mocked LLM."""
        # Setup mock - create a simple mock with generate_response method
        mock_llm = Mock()
        mock_llm.generate_response.return_value = "[[Tag: Python异步编程, FastAPI依赖注入, 装饰器模式]]"

        generator = DiaryTagGenerator()
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

        generator = DiaryTagGenerator()
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
        generator = DiaryTagGenerator()

        response = "[[Tag: Python编程, 异步开发, FastAPI框架]]"
        tags = generator._parse_tags(response)

        assert len(tags) == 3
        assert "Python编程" in tags
        assert "异步开发" in tags
        assert "FastAPI框架" in tags

    def test_parse_tags_with_invalid_format_fallback(self):
        """Test parsing tags falls back to line-by-line extraction."""
        generator = DiaryTagGenerator()

        response = """Python编程
异步开发
FastAPI框架"""
        tags = generator._parse_tags(response)

        assert len(tags) >= 1

    def test_parse_tags_limits_to_five(self):
        """Test that parsing limits to 5 tags."""
        generator = DiaryTagGenerator()

        response = "[[Tag: 标签1, 标签2, 标签3, 标签4, 标签5, 标签6, 标签7, 标签8, 标签9, 标签10]]"
        tags = generator._parse_tags(response)

        assert len(tags) == 5

    @patch('app.services.diary.tag_generator.LLMBase')
    def test_build_tag_prompt_knowledge_category(self, mock_llm_base):
        """Test prompt building for knowledge category."""
        generator = DiaryTagGenerator()
        prompt = generator._build_tag_prompt(
            diary_content="学习了Python装饰器",
            category="knowledge"
        )

        assert "knowledge" in prompt
        assert "Python装饰器" in prompt
        assert "高密度" in prompt

    @patch('app.services.diary.tag_generator.LLMBase')
    def test_build_tag_prompt_emotional_category(self, mock_llm_base):
        """Test prompt building for emotional category."""
        generator = DiaryTagGenerator()
        prompt = generator._build_tag_prompt(
            diary_content="哥哥涨工资了，很开心",
            category="emotional"
        )

        assert "emotional" in prompt
        assert "涨工资" in prompt
        assert "情绪触发源" in prompt
