"""
Unit and integration tests for DeepSeekLLM service.

Tests for DeepSeek LLM service including initialization, response generation,
and tool calling functionality.
"""
import os
from unittest.mock import Mock, patch

import pytest

from app.configs.llms.base import BaseLlmConfig
from app.configs.llms.deepseek import DeepSeekConfig
from app.services.llms.deepseek import DeepSeekLLM


@pytest.mark.unit
class TestDeepSeekLLMInit:
    """Tests for DeepSeekLLM initialization."""

    def test_deepseek_init_with_deepseek_config(self):
        """Test DeepSeekLLM initialization with DeepSeekConfig."""
        config = DeepSeekConfig(
            model="deepseek-coder",
            api_key="test-api-key",
            deepseek_base_url="https://test-url.com",
        )

        with patch("app.services.llms.deepseek.OpenAI"):
            llm = DeepSeekLLM(config)

            assert llm.config.model == "deepseek-coder"
            assert llm.config.api_key == "test-api-key"
            assert llm.config.deepseek_base_url == "https://test-url.com"

    def test_deepseek_init_with_dict(self):
        """Test DeepSeekLLM initialization with dict config."""
        config_dict = {
            "model": "deepseek-chat",
            "api_key": "dict-api-key",
            "temperature": 0.5,
        }

        with patch("app.services.llms.deepseek.OpenAI"):
            llm = DeepSeekLLM(config_dict)

            assert llm.config.model == "deepseek-chat"
            assert llm.config.api_key == "dict-api-key"
            assert llm.config.temperature == 0.5

    def test_deepseek_init_default_model(self):
        """Test DeepSeekLLM initialization with default model."""
        with patch("app.services.llms.deepseek.OpenAI"):
            llm = DeepSeekLLM()

            assert llm.config.model == "deepseek-chat"

    def test_deepseek_init_base_config_conversion(self):
        """Test DeepSeekLLM initialization with BaseLlmConfig conversion."""
        base_config = BaseLlmConfig(
            model="custom-model",
            api_key="base-api-key",
            temperature=0.9,
        )

        with patch("app.services.llms.deepseek.OpenAI"):
            llm = DeepSeekLLM(base_config)

            assert isinstance(llm.config, DeepSeekConfig)
            assert llm.config.model == "custom-model"
            assert llm.config.api_key == "base-api-key"
            assert llm.config.temperature == 0.9

    def test_deepseek_init_no_config(self):
        """Test DeepSeekLLM initialization without config."""
        with patch("app.services.llms.deepseek.OpenAI"):
            llm = DeepSeekLLM()

            assert isinstance(llm.config, DeepSeekConfig)
            assert llm.config.model == "deepseek-chat"


@pytest.mark.unit
class TestDeepSeekLLMGenerateResponse:
    """Tests for DeepSeekLLM response generation with mocked API."""

    def test_deepseek_generate_response_mock(self, mocker, test_messages, mock_openai_response):
        """Test DeepSeekLLM generate_response with mocked API."""
        # Mock the OpenAI client
        mock_openai = mocker.patch("app.services.llms.deepseek.OpenAI")
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_openai.return_value = mock_client

        llm = DeepSeekLLM()
        response = llm.generate_response(test_messages)

        # Verify the response
        assert response == "This is a mock response from the LLM."

        # Verify the API was called correctly
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "deepseek-chat"
        assert call_args[1]["messages"] == test_messages

    def test_deepseek_generate_response_with_tools_mock(
        self, mocker, test_messages, test_tools, mock_openai_response_with_tool_call
    ):
        """Test DeepSeekLLM generate_response with tools and mocked API."""
        mock_openai = mocker.patch("app.services.llms.deepseek.OpenAI")
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response_with_tool_call
        mock_openai.return_value = mock_client

        llm = DeepSeekLLM()
        response = llm.generate_response(test_messages, tools=test_tools)

        # Verify the response structure
        assert response["content"] == "I'll check the weather for you."
        assert len(response["tool_calls"]) == 1
        assert response["tool_calls"][0]["name"] == "get_weather"
        assert response["tool_calls"][0]["arguments"] == {"location": "Beijing"}

    def test_deepseek_generate_response_with_custom_params(self, mocker, test_messages, mock_openai_response):
        """Test DeepSeekLLM generate_response with custom parameters."""
        mock_openai = mocker.patch("app.services.llms.deepseek.OpenAI")
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_openai.return_value = mock_client

        config = DeepSeekConfig(temperature=0.9, max_tokens=1000)
        llm = DeepSeekLLM(config)
        llm.generate_response(test_messages)

        # Verify custom parameters were passed
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.9
        assert call_args[1]["max_tokens"] == 1000


@pytest.mark.unit
class TestDeepSeekLLMParseResponse:
    """Tests for DeepSeekLLM response parsing."""

    def test_deepseek_parse_response_text(self, mocker, mock_openai_response):
        """Test parsing a text response (no tools)."""
        with patch("app.services.llms.deepseek.OpenAI"):
            llm = DeepSeekLLM()
            response = llm._parse_response(mock_openai_response, tools=None)

            assert response == "This is a mock response from the LLM."

    def test_deepseek_parse_response_with_tools(self, mocker, mock_openai_response_with_tool_call):
        """Test parsing a response with tool calls."""
        with patch("app.services.llms.deepseek.OpenAI"):
            llm = DeepSeekLLM()
            response = llm._parse_response(mock_openai_response_with_tool_call, tools=[{}])

            assert response["content"] == "I'll check the weather for you."
            assert len(response["tool_calls"]) == 1
            assert response["tool_calls"][0]["name"] == "get_weather"
            assert response["tool_calls"][0]["arguments"] == {"location": "Beijing"}

    def test_deepseek_parse_response_with_tools_no_calls(self, mocker, mock_openai_response):
        """Test parsing a response when tools are provided but no calls are made."""
        with patch("app.services.llms.deepseek.OpenAI"):
            llm = DeepSeekLLM()
            response = llm._parse_response(mock_openai_response, tools=[{}])

            assert response["content"] == "This is a mock response from the LLM."
            assert response["tool_calls"] == []


@pytest.mark.unit
class TestDeepSeekLLMStreamResponse:
    """Tests for DeepSeekLLM streaming response generation."""

    def test_deepseek_generate_response_stream_mock(self, mocker, test_messages):
        """Test DeepSeekLLM generate_response_stream with mocked API."""
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
        mock_openai = mocker.patch("app.services.llms.deepseek.OpenAI")
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = [mock_chunk1, mock_chunk2, mock_chunk3]
        mock_openai.return_value = mock_client

        llm = DeepSeekLLM()
        chunks = list(llm.generate_response_stream(test_messages))

        # Verify the chunks
        assert chunks == ["Hello", " World"]
        assert len(chunks) == 2

        # Verify the API was called with stream=True
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["stream"] is True

    def test_deepseek_generate_response_stream_empty_chunks(self, mocker, test_messages):
        """Test DeepSeekLLM generate_response_stream with empty response."""
        # Mock the OpenAI client
        mock_openai = mocker.patch("app.services.llms.deepseek.OpenAI")
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = []
        mock_openai.return_value = mock_client

        llm = DeepSeekLLM()
        chunks = list(llm.generate_response_stream(test_messages))

        # Verify empty response
        assert chunks == []

    def test_deepseek_generate_response_stream_with_custom_params(self, mocker, test_messages):
        """Test DeepSeekLLM generate_response_stream with custom parameters."""
        mock_chunk = Mock()
        mock_chunk.choices = []

        mock_openai = mocker.patch("app.services.llms.deepseek.OpenAI")
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = [mock_chunk]
        mock_openai.return_value = mock_client

        config = DeepSeekConfig(temperature=0.9, max_tokens=1000)
        llm = DeepSeekLLM(config)
        list(llm.generate_response_stream(test_messages))

        # Verify custom parameters were passed
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["temperature"] == 0.9
        assert call_args[1]["max_tokens"] == 1000
        assert call_args[1]["stream"] is True


@pytest.mark.integration
class TestDeepSeekLLMIntegration:
    """Integration tests for DeepSeekLLM with real API calls."""

    @pytest.mark.skipif(
        os.getenv("DEEPSEEK_API_KEY") is None,
        reason="DEEPSEEK_API_KEY environment variable not set"
    )
    def test_deepseek_integration_simple(self, test_messages):
        """Test DeepSeekLLM with real API call for simple response."""
        llm = DeepSeekLLM()
        response = llm.generate_response(test_messages)

        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\nDeepSeek simple response: {response}")

    @pytest.mark.skipif(
        os.getenv("DEEPSEEK_API_KEY") is None,
        reason="DEEPSEEK_API_KEY environment variable not set"
    )
    def test_deepseek_integration_with_tools(self, test_messages, test_tools):
        """Test DeepSeekLLM with real API call with tool definitions."""
        llm = DeepSeekLLM()
        response = llm.generate_response(test_messages, tools=test_tools)

        assert isinstance(response, dict)
        assert "content" in response
        assert "tool_calls" in response
        print(f"\nDeepSeek tools response content: {response['content']}")
        print(f"DeepSeek tool calls: {response['tool_calls']}")

    @pytest.mark.skipif(
        os.getenv("DEEPSEEK_API_KEY") is None,
        reason="DEEPSEEK_API_KEY environment variable not set"
    )
    def test_deepseek_integration_custom_model(self, test_messages):
        """Test DeepSeekLLM with a custom model."""
        config = DeepSeekConfig(model="deepseek-coder")
        llm = DeepSeekLLM(config)
        response = llm.generate_response(test_messages)

        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\nDeepSeek-coder response: {response}")

    @pytest.mark.skipif(
        os.getenv("DEEPSEEK_API_KEY") is None,
        reason="DEEPSEEK_API_KEY environment variable not set"
    )
    def test_deepseek_integration_stream_simple(self, test_messages):
        """Test DeepSeekLLM streaming response with real API call."""
        llm = DeepSeekLLM()
        chunks = []
        for chunk in llm.generate_response_stream(test_messages):
            chunks.append(chunk)
            print(chunk, end="", flush=True)

        full_response = "".join(chunks)
        print()  # New line after streaming

        assert len(chunks) > 0
        assert len(full_response) > 0
        print(f"\nDeepSeek stream response: {full_response[:100]}...")

    @pytest.mark.skipif(
        os.getenv("DEEPSEEK_API_KEY") is None,
        reason="DEEPSEEK_API_KEY environment variable not set"
    )
    def test_deepseek_integration_stream_custom_model(self, test_messages):
        """Test DeepSeekLLM streaming response with a custom model."""
        config = DeepSeekConfig(model="deepseek-coder")
        llm = DeepSeekLLM(config)
        chunks = list(llm.generate_response_stream(test_messages))

        full_response = "".join(chunks)

        assert len(chunks) > 0
        assert len(full_response) > 0
        print(f"\nDeepSeek-coder stream response: {full_response[:100]}...")
