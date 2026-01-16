"""
Unit tests for LLMBase abstract class.

Tests for the base LLM class functionality including validation,
reasoning model detection, and parameter handling.
"""
import pytest

from app.configs.llms.base import BaseLlmConfig
from app.configs.llms.qwen import QWENConfig
from app.services.llms.base import LLMBase
from app.services.llms.qwen import QwenLLM


# Concrete implementation for testing abstract base class
class ConcreteLLM(LLMBase):
    """Concrete implementation of LLMBase for testing."""

    def generate_response(self, messages, tools=None, tool_choice="auto", **kwargs):
        """Concrete implementation of abstract method."""
        return "Concrete response"

    def generate_response_stream(self, messages, tools=None, tool_choice="auto", **kwargs):
        """Concrete implementation of abstract stream method."""
        yield "Concrete stream response"


@pytest.mark.unit
class TestLLMBaseValidateConfig:
    """Tests for LLMBase config validation."""

    def test_base_validate_config_with_model(self):
        """Test validation with config that has model attribute."""
        config = BaseLlmConfig(model="test-model")
        llm = ConcreteLLM(config)

        # Should not raise any error
        assert llm.config.model == "test-model"

    def test_base_validate_config_without_model(self):
        """Test validation raises error when config has no model attribute."""
        # Create a config-like object without model
        class InvalidConfig:
            pass

        config = InvalidConfig()

        with pytest.raises(ValueError, match="Configuration must have a 'model' attribute"):
            ConcreteLLM(config)

    def test_base_init_with_none_config(self):
        """Test initialization with None config uses default BaseLlmConfig."""
        llm = ConcreteLLM(None)

        assert isinstance(llm.config, BaseLlmConfig)
        assert llm.config.model is None

    def test_base_init_with_dict_config(self):
        """Test initialization with dict config."""
        config_dict = {"model": "dict-model", "temperature": 0.7}
        llm = ConcreteLLM(config_dict)

        assert llm.config.model == "dict-model"
        assert llm.config.temperature == 0.7


@pytest.mark.unit
class TestLLMBaseIsReasoningModel:
    """Tests for LLMBase reasoning model detection."""

    def test_base_is_reasoning_model_o1(self):
        """Test o1 model is detected as reasoning model."""
        llm = ConcreteLLM()
        assert llm._is_reasoning_model("o1") is True
        assert llm._is_reasoning_model("o1-preview") is True

    def test_base_is_reasoning_model_o3(self):
        """Test o3 model is detected as reasoning model."""
        llm = ConcreteLLM()
        assert llm._is_reasoning_model("o3-mini") is True
        assert llm._is_reasoning_model("o3") is True

    def test_base_is_reasoning_model_gpt5(self):
        """Test GPT-5 series models are detected as reasoning models."""
        llm = ConcreteLLM()
        assert llm._is_reasoning_model("gpt-5") is True
        assert llm._is_reasoning_model("gpt-5o") is True
        assert llm._is_reasoning_model("gpt-5o-mini") is True
        assert llm._is_reasoning_model("gpt-5o-micro") is True

    def test_base_is_reasoning_model_case_insensitive(self):
        """Test reasoning model detection is case-insensitive."""
        llm = ConcreteLLM()
        assert llm._is_reasoning_model("O1") is True
        assert llm._is_reasoning_model("GPT-5") is True
        assert llm._is_reasoning_model("O3-MINI") is True

    def test_base_is_not_reasoning_model(self):
        """Test regular models are not detected as reasoning models."""
        llm = ConcreteLLM()
        assert llm._is_reasoning_model("gpt-4") is False
        assert llm._is_reasoning_model("gpt-3.5-turbo") is False
        assert llm._is_reasoning_model("claude-3-5-sonnet") is False
        assert llm._is_reasoning_model("qwen-turbo") is False
        assert llm._is_reasoning_model("deepseek-chat") is False


@pytest.mark.unit
class TestLLMBaseGetCommonParams:
    """Tests for LLMBase common parameters extraction."""

    def test_base_get_common_params_defaults(self):
        """Test get_common_params returns default parameters."""
        config = BaseLlmConfig()
        llm = ConcreteLLM(config)
        params = llm._get_common_params()

        assert params["temperature"] == 0.1
        assert params["max_tokens"] == 2000
        assert params["top_p"] == 0.1

    def test_base_get_common_params_custom(self):
        """Test get_common_params returns custom parameters."""
        config = BaseLlmConfig(temperature=0.9, max_tokens=1000, top_p=0.95)
        llm = ConcreteLLM(config)
        params = llm._get_common_params()

        assert params["temperature"] == 0.9
        assert params["max_tokens"] == 1000
        assert params["top_p"] == 0.95

    def test_base_get_common_params_with_kwargs(self):
        """Test get_common_params includes additional kwargs."""
        llm = ConcreteLLM()
        params = llm._get_common_params(custom_param="custom_value")

        assert params["custom_param"] == "custom_value"
        # Default params should still be present
        assert params["temperature"] == 0.1


@pytest.mark.unit
class TestLLMBaseGetSupportedParams:
    """Tests for LLMBase supported parameters filtering."""

    def test_base_get_supported_params_regular_model(self):
        """Test regular models get all parameters including temperature."""
        config = BaseLlmConfig(model="gpt-4", temperature=0.7)
        llm = ConcreteLLM(config)

        messages = [{"role": "user", "content": "Hello"}]
        params = llm._get_supported_params(messages=messages)

        # Regular models should get all common params
        assert "temperature" in params
        assert "max_tokens" in params
        assert "top_p" in params
        assert params["temperature"] == 0.7

    def test_base_get_supported_params_reasoning_model(self):
        """Test reasoning models get limited parameters."""
        config = BaseLlmConfig(model="o1", temperature=0.7)
        llm = ConcreteLLM(config)

        messages = [{"role": "user", "content": "Hello"}]
        params = llm._get_supported_params(messages=messages)

        # Reasoning models should NOT have temperature, max_tokens, top_p
        assert "temperature" not in params
        assert "max_tokens" not in params
        assert "top_p" not in params
        # But should have messages
        assert "messages" in params

    def test_base_get_supported_params_with_response_format(self):
        """Test response_format is included for reasoning models."""
        config = BaseLlmConfig(model="o1")
        llm = ConcreteLLM(config)

        messages = [{"role": "user", "content": "Hello"}]
        response_format = {"type": "json_object"}
        params = llm._get_supported_params(messages=messages, response_format=response_format)

        assert "response_format" in params
        assert params["response_format"] == response_format

    def test_base_get_supported_params_with_tools(self):
        """Test tools are included for reasoning models."""
        config = BaseLlmConfig(model="o1")
        llm = ConcreteLLM(config)

        messages = [{"role": "user", "content": "Hello"}]
        tools = [{"type": "function", "function": {"name": "test"}}]
        tool_choice = "auto"
        params = llm._get_supported_params(messages=messages, tools=tools, tool_choice=tool_choice)

        assert "tools" in params
        assert params["tools"] == tools
        assert "tool_choice" in params
        assert params["tool_choice"] == tool_choice

    def test_base_get_supported_params_gpt5_series(self):
        """Test GPT-5 series models are treated as reasoning models."""
        config = BaseLlmConfig(model="gpt-5o-mini", temperature=0.7)
        llm = ConcreteLLM(config)

        messages = [{"role": "user", "content": "Hello"}]
        params = llm._get_supported_params(messages=messages)

        # GPT-5 models should NOT have temperature
        assert "temperature" not in params
        assert "messages" in params
