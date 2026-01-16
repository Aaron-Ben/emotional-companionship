"""
Unit and integration tests for QwenLLM service.

Tests for Qwen LLM service including initialization, response generation,
and tool calling functionality.
"""
import json
import os
from unittest.mock import Mock, patch

import pytest

from app.configs.llms.base import BaseLlmConfig
from app.configs.llms.qwen import QWENConfig
from app.services.llms.qwen import QwenLLM


@pytest.mark.unit
class TestQwenLLMInit:
    """Tests for QwenLLM initialization."""

    def test_qwen_init_with_qwen_config(self):
        """Test QwenLLM initialization with QWENConfig."""
        config = QWENConfig(
            model="qwen-max",
            api_key="test-api-key",
            qwen_base_url="https://test-url.com",
        )

        with patch("app.services.llms.qwen.OpenAI"):
            llm = QwenLLM(config)

            assert llm.config.model == "qwen-max"
            assert llm.config.api_key == "test-api-key"
            assert llm.config.qwen_base_url == "https://test-url.com"

    def test_qwen_init_with_dict(self):
        """Test QwenLLM initialization with dict config."""
        config_dict = {
            "model": "qwen-turbo",
            "api_key": "dict-api-key",
            "temperature": 0.5,
        }

        with patch("app.services.llms.qwen.OpenAI"):
            llm = QwenLLM(config_dict)

            assert llm.config.model == "qwen-turbo"
            assert llm.config.api_key == "dict-api-key"
            assert llm.config.temperature == 0.5

    def test_qwen_init_default_model(self):
        """Test QwenLLM initialization with default model."""
        with patch("app.services.llms.qwen.OpenAI"):
            llm = QwenLLM()

            assert llm.config.model == "qwen-turbo"

    def test_qwen_init_base_config_conversion(self):
        """Test QwenLLM initialization with BaseLlmConfig conversion."""
        base_config = BaseLlmConfig(
            model="custom-model",
            api_key="base-api-key",
            temperature=0.9,
        )

        with patch("app.services.llms.qwen.OpenAI"):
            llm = QwenLLM(base_config)

            assert isinstance(llm.config, QWENConfig)
            assert llm.config.model == "custom-model"
            assert llm.config.api_key == "base-api-key"
            assert llm.config.temperature == 0.9

    def test_qwen_init_no_config(self):
        """Test QwenLLM initialization without config."""
        with patch("app.services.llms.qwen.OpenAI"):
            llm = QwenLLM()

            assert isinstance(llm.config, QWENConfig)
            assert llm.config.model == "qwen-turbo"


@pytest.mark.unit
class TestQwenLLMGenerateResponse:
    """Tests for QwenLLM response generation with mocked API."""

    def test_qwen_generate_response_mock(self, mocker, test_messages, mock_openai_response):
        """Test QwenLLM generate_response with mocked API."""
        # Mock the OpenAI client
        mock_openai = mocker.patch("app.services.llms.qwen.OpenAI")
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_openai.return_value = mock_client

        llm = QwenLLM()
        response = llm.generate_response(test_messages)

        # Verify the response
        assert response == "This is a mock response from the LLM."

        # Verify the API was called correctly
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "qwen-turbo"
        assert call_args[1]["messages"] == test_messages

    def test_qwen_generate_response_with_tools_mock(
        self, mocker, test_messages, test_tools, mock_openai_response_with_tool_call
    ):
        """Test QwenLLM generate_response with tools and mocked API."""
        mock_openai = mocker.patch("app.services.llms.qwen.OpenAI")
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response_with_tool_call
        mock_openai.return_value = mock_client

        llm = QwenLLM()
        response = llm.generate_response(test_messages, tools=test_tools)

        # Verify the response structure
        assert response["content"] == "I'll check the weather for you."
        assert len(response["tool_calls"]) == 1
        assert response["tool_calls"][0]["name"] == "get_weather"
        assert response["tool_calls"][0]["arguments"] == {"location": "Beijing"}

    def test_qwen_generate_response_with_custom_params(self, mocker, test_messages, mock_openai_response):
        """Test QwenLLM generate_response with custom parameters."""
        mock_openai = mocker.patch("app.services.llms.qwen.OpenAI")
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_openai.return_value = mock_client

        config = QWENConfig(temperature=0.9, max_tokens=1000)
        llm = QwenLLM(config)
        llm.generate_response(test_messages)

        # Verify custom parameters were passed
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.9
        assert call_args[1]["max_tokens"] == 1000


@pytest.mark.unit
class TestQwenLLMParseResponse:
    """Tests for QwenLLM response parsing."""

    def test_qwen_parse_response_text(self, mocker, mock_openai_response):
        """Test parsing a text response (no tools)."""
        with patch("app.services.llms.qwen.OpenAI"):
            llm = QwenLLM()
            response = llm._parse_response(mock_openai_response, tools=None)

            assert response == "This is a mock response from the LLM."

    def test_qwen_parse_response_with_tools(self, mocker, mock_openai_response_with_tool_call):
        """Test parsing a response with tool calls."""
        with patch("app.services.llms.qwen.OpenAI"):
            llm = QwenLLM()
            response = llm._parse_response(mock_openai_response_with_tool_call, tools=[{}])

            assert response["content"] == "I'll check the weather for you."
            assert len(response["tool_calls"]) == 1
            assert response["tool_calls"][0]["name"] == "get_weather"
            assert response["tool_calls"][0]["arguments"] == {"location": "Beijing"}

    def test_qwen_parse_response_with_tools_no_calls(self, mocker, mock_openai_response):
        """Test parsing a response when tools are provided but no calls are made."""
        with patch("app.services.llms.qwen.OpenAI"):
            llm = QwenLLM()
            response = llm._parse_response(mock_openai_response, tools=[{}])

            assert response["content"] == "This is a mock response from the LLM."
            assert response["tool_calls"] == []


@pytest.mark.unit
class TestQwenLLMStreamResponse:
    """Tests for QwenLLM streaming response generation."""

    def test_qwen_generate_response_stream_mock(self, mocker, test_messages):
        """Test QwenLLM generate_response_stream with mocked API."""
        from unittest.mock import MagicMock

        # Create mock stream chunks
        mock_chunk1 = Mock()
        mock_choice1 = Mock()
        mock_delta1 = Mock()
        mock_delta1.content = "Hello"
        mock_choice1.delta = mock_delta1
        mock_chunk1.choices = [mock_choice1]

        mock_chunk2 = Mock()
        mock_choice2 = Mock()
        mock_delta2 = Mock()
        mock_delta2.content = " World"
        mock_choice2.delta = mock_delta2
        mock_chunk2.choices = [mock_choice2]

        mock_chunk3 = Mock()
        mock_chunk3.choices = []

        # Mock the OpenAI client
        mock_openai = mocker.patch("app.services.llms.qwen.OpenAI")
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = [mock_chunk1, mock_chunk2, mock_chunk3]
        mock_openai.return_value = mock_client

        llm = QwenLLM()
        chunks = list(llm.generate_response_stream(test_messages))

        # Verify the chunks
        assert chunks == ["Hello", " World"]
        assert len(chunks) == 2

        # Verify the API was called with stream=True
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["stream"] is True

    def test_qwen_generate_response_stream_empty_chunks(self, mocker, test_messages):
        """Test QwenLLM generate_response_stream with empty response."""
        # Mock the OpenAI client
        mock_openai = mocker.patch("app.services.llms.qwen.OpenAI")
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = []
        mock_openai.return_value = mock_client

        llm = QwenLLM()
        chunks = list(llm.generate_response_stream(test_messages))

        # Verify empty response
        assert chunks == []

    def test_qwen_generate_response_stream_with_custom_params(self, mocker, test_messages):
        """Test QwenLLM generate_response_stream with custom parameters."""
        mock_chunk = Mock()
        mock_chunk.choices = []

        mock_openai = mocker.patch("app.services.llms.qwen.OpenAI")
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = [mock_chunk]
        mock_openai.return_value = mock_client

        config = QWENConfig(temperature=0.9, max_tokens=1000)
        llm = QwenLLM(config)
        list(llm.generate_response_stream(test_messages))

        # Verify custom parameters were passed
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.9
        assert call_args[1]["max_tokens"] == 1000
        assert call_args[1]["stream"] is True


@pytest.mark.integration
class TestQwenLLMIntegration:
    """Integration tests for QwenLLM with real API calls."""

    @pytest.mark.skipif(
        os.getenv("DASHSCOPE_API_KEY") is None,
        reason="DASHSCOPE_API_KEY environment variable not set"
    )
    def test_qwen_integration_simple(self, test_messages):
        """Test QwenLLM with real API call for simple response."""
        llm = QwenLLM()
        response = llm.generate_response(test_messages)

        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\nQwen simple response: {response}")

    @pytest.mark.skipif(
        os.getenv("DASHSCOPE_API_KEY") is None,
        reason="DASHSCOPE_API_KEY environment variable not set"
    )
    def test_qwen_integration_with_tools(self, test_messages, test_tools):
        """Test QwenLLM with real API call with tool definitions."""
        llm = QwenLLM()
        response = llm.generate_response(test_messages, tools=test_tools)

        assert isinstance(response, dict)
        assert "content" in response
        assert "tool_calls" in response
        print(f"\nQwen tools response content: {response['content']}")
        print(f"Qwen tool calls: {response['tool_calls']}")

    @pytest.mark.skipif(
        os.getenv("DASHSCOPE_API_KEY") is None,
        reason="DASHSCOPE_API_KEY environment variable not set"
    )
    def test_qwen_integration_custom_model(self, test_messages):
        """Test QwenLLM with a custom model."""
        config = QWENConfig(model="qwen-plus")
        llm = QwenLLM(config)
        response = llm.generate_response(test_messages)

        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\nQwen-plus response: {response}")

    @pytest.mark.skipif(
        os.getenv("DASHSCOPE_API_KEY") is None,
        reason="DASHSCOPE_API_KEY environment variable not set"
    )
    def test_qwen_integration_stream_simple(self, test_messages):
        """Test QwenLLM streaming response with real API call."""
        llm = QwenLLM()
        chunks = []
        for chunk in llm.generate_response_stream(test_messages):
            chunks.append(chunk)
            print(chunk, end="", flush=True)

        full_response = "".join(chunks)
        print()  # New line after streaming

        assert len(chunks) > 0
        assert len(full_response) > 0
        print(f"\nQwen stream response: {full_response[:100]}...")

    @pytest.mark.skipif(
        os.getenv("DASHSCOPE_API_KEY") is None,
        reason="DASHSCOPE_API_KEY environment variable not set"
    )
    def test_qwen_integration_stream_custom_model(self, test_messages):
        """Test QwenLLM streaming response with a custom model."""
        config = QWENConfig(model="qwen-plus")
        llm = QwenLLM(config)
        chunks = list(llm.generate_response_stream(test_messages))

        full_response = "".join(chunks)

        assert len(chunks) > 0
        assert len(full_response) > 0
        print(f"\nQwen-plus stream response: {full_response[:100]}...")
