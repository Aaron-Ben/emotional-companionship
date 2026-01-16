"""
Unit tests for LLM configuration classes.

Tests for BaseLlmConfig, QWENConfig, and DeepSeekConfig classes.
"""
import pytest

from app.configs.llms.base import BaseLlmConfig
from app.configs.llms.qwen import QWENConfig
from app.configs.llms.deepseek import DeepSeekConfig


@pytest.mark.unit
class TestBaseLlmConfig:
    """Tests for BaseLlmConfig class."""

    def test_base_config_default_values(self):
        """Test BaseLlmConfig with default values."""
        config = BaseLlmConfig()

        assert config.model is None
        assert config.temperature == 0.1
        assert config.api_key is None
        assert config.max_tokens == 2000
        assert config.top_p == 0.1
        assert config.top_k == 1
        assert config.enable_vision is False
        assert config.vision_details == "auto"
        assert config.http_client_proxies is None

    def test_base_config_with_all_parameters(self):
        """Test BaseLlmConfig with all parameters set."""
        config = BaseLlmConfig(
            model="test-model",
            temperature=0.7,
            api_key="test-api-key",
            max_tokens=1000,
            top_p=0.9,
            top_k=5,
            enable_vision=True,
            vision_details="high",
            http_client_proxies={"http": "http://proxy"},
        )

        assert config.model == "test-model"
        assert config.temperature == 0.7
        assert config.api_key == "test-api-key"
        assert config.max_tokens == 1000
        assert config.top_p == 0.9
        assert config.top_k == 5
        assert config.enable_vision is True
        assert config.vision_details == "high"
        assert config.http_client_proxies == {"http": "http://proxy"}

    def test_base_config_with_partial_parameters(self):
        """Test BaseLlmConfig with only some parameters set."""
        config = BaseLlmConfig(
            model="gpt-4",
            temperature=0.5,
        )

        assert config.model == "gpt-4"
        assert config.temperature == 0.5
        # Other parameters should have default values
        assert config.api_key is None
        assert config.max_tokens == 2000

    def test_base_config_with_dict_proxies(self):
        """Test BaseLlmConfig with dict proxy configuration."""
        proxies = {"http": "http://proxy.example.com", "https": "https://proxy.example.com"}
        config = BaseLlmConfig(http_client_proxies=proxies)

        assert config.http_client_proxies == proxies

    def test_base_config_with_string_proxies(self):
        """Test BaseLlmConfig with string proxy configuration."""
        proxies = "http://proxy.example.com"
        config = BaseLlmConfig(http_client_proxies=proxies)

        assert config.http_client_proxies == proxies


@pytest.mark.unit
class TestQWENConfig:
    """Tests for QWENConfig class."""

    def test_qwen_config_default_values(self):
        """Test QWENConfig with default values."""
        config = QWENConfig()

        # Base config attributes should have defaults
        assert config.model is None
        assert config.temperature == 0.1
        assert config.api_key is None
        assert config.max_tokens == 2000
        assert config.top_p == 0.1
        assert config.top_k == 1
        assert config.enable_vision is False
        assert config.vision_details == "auto"
        assert config.http_client_proxies is None

        # Qwen-specific attribute
        assert config.qwen_base_url is None

    def test_qwen_config_with_all_parameters(self):
        """Test QWENConfig with all parameters set."""
        config = QWENConfig(
            model="qwen-max",
            temperature=0.8,
            api_key="qwen-api-key",
            max_tokens=3000,
            top_p=0.95,
            top_k=10,
            enable_vision=True,
            vision_details="low",
            http_client_proxies={"http": "http://proxy"},
            qwen_base_url="https://custom-qwen-url.com",
        )

        # Verify base config attributes
        assert config.model == "qwen-max"
        assert config.temperature == 0.8
        assert config.api_key == "qwen-api-key"
        assert config.max_tokens == 3000
        assert config.top_p == 0.95
        assert config.top_k == 10
        assert config.enable_vision is True
        assert config.vision_details == "low"
        assert config.http_client_proxies == {"http": "http://proxy"}

        # Verify Qwen-specific attribute
        assert config.qwen_base_url == "https://custom-qwen-url.com"

    def test_qwen_config_inheritance(self):
        """Test that QWENConfig properly inherits from BaseLlmConfig."""
        config = QWENConfig(model="qwen-turbo")

        # Should be an instance of both QWENConfig and BaseLlmConfig
        assert isinstance(config, QWENConfig)
        assert isinstance(config, BaseLlmConfig)


@pytest.mark.unit
class TestDeepSeekConfig:
    """Tests for DeepSeekConfig class."""

    def test_deepseek_config_default_values(self):
        """Test DeepSeekConfig with default values."""
        config = DeepSeekConfig()

        # Base config attributes should have defaults
        assert config.model is None
        assert config.temperature == 0.1
        assert config.api_key is None
        assert config.max_tokens == 2000
        assert config.top_p == 0.1
        assert config.top_k == 1
        assert config.enable_vision is False
        assert config.vision_details == "auto"
        assert config.http_client_proxies is None

        # DeepSeek-specific attribute
        assert config.deepseek_base_url is None

    def test_deepseek_config_with_all_parameters(self):
        """Test DeepSeekConfig with all parameters set."""
        config = DeepSeekConfig(
            model="deepseek-coder",
            temperature=0.6,
            api_key="deepseek-api-key",
            max_tokens=4000,
            top_p=0.85,
            top_k=15,
            enable_vision=True,
            vision_details="high",
            http_client_proxies={"http": "http://proxy"},
            deepseek_base_url="https://custom-deepseek-url.com",
        )

        # Verify base config attributes
        assert config.model == "deepseek-coder"
        assert config.temperature == 0.6
        assert config.api_key == "deepseek-api-key"
        assert config.max_tokens == 4000
        assert config.top_p == 0.85
        assert config.top_k == 15
        assert config.enable_vision is True
        assert config.vision_details == "high"
        assert config.http_client_proxies == {"http": "http://proxy"}

        # Verify DeepSeek-specific attribute
        assert config.deepseek_base_url == "https://custom-deepseek-url.com"

    def test_deepseek_config_inheritance(self):
        """Test that DeepSeekConfig properly inherits from BaseLlmConfig."""
        config = DeepSeekConfig(model="deepseek-chat")

        # Should be an instance of both DeepSeekConfig and BaseLlmConfig
        assert isinstance(config, DeepSeekConfig)
        assert isinstance(config, BaseLlmConfig)
