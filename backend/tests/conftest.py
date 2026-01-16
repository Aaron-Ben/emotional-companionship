"""
Pytest configuration file for LLM tests.

This file contains shared fixtures and configuration for testing
Qianwen (Qwen) and DeepSeek LLM services.
"""
import os
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock

import pytest
from dotenv import load_dotenv


def pytest_configure(config):
    """Configure pytest with custom markers and load environment variables."""
    config.addinivalue_line("markers", "unit: Mark test as a unit test (mocked API)")
    config.addinivalue_line("markers", "integration: Mark test as an integration test (real API)")

    # Load .env file from project root
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)


@pytest.fixture
def test_messages() -> List[Dict[str, str]]:
    """Standard test messages for LLM requests."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ]


@pytest.fixture
def test_messages_with_tools() -> List[Dict[str, str]]:
    """Test messages that expect tool calls."""
    return [
        {"role": "system", "content": "You are a helpful assistant with access to tools."},
        {"role": "user", "content": "What's the weather in Beijing?"},
    ]


@pytest.fixture
def test_tools() -> List[Dict]:
    """Sample tool definitions for tool calling tests."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        }
                    },
                    "required": ["location"],
                },
            },
        }
    ]


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI chat completion response object."""
    mock_response = Mock()

    # Mock the choices structure
    mock_choice = Mock()
    mock_message = Mock()
    mock_message.content = "This is a mock response from the LLM."
    mock_message.tool_calls = None
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    return mock_response


@pytest.fixture
def mock_openai_response_with_tool_call():
    """Create a mock OpenAI response with tool calls."""
    import json

    mock_response = Mock()

    # Mock the choices structure with tool calls
    mock_choice = Mock()
    mock_message = Mock()
    mock_message.content = "I'll check the weather for you."

    # Mock tool calls
    mock_tool_call = Mock()
    mock_tool_call.function.name = "get_weather"
    mock_tool_call.function.arguments = json.dumps({"location": "Beijing"})

    mock_message.tool_calls = [mock_tool_call]
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    return mock_response


@pytest.fixture
def dashscope_api_key() -> str:
    """Get the Dashscope (Qwen) API key from environment."""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        pytest.skip("DASHSCOPE_API_KEY environment variable not set")
    return api_key


@pytest.fixture
def deepseek_api_key() -> str:
    """Get the DeepSeek API key from environment."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY environment variable not set")
    return api_key


@pytest.fixture
def qwen_base_url() -> str:
    """Get the Qwen base URL from environment or use default."""
    return os.getenv("QWEN_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")


@pytest.fixture
def deepseek_base_url() -> str:
    """Get the DeepSeek base URL from environment or use default."""
    return os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
