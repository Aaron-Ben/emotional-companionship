import json
import os
from typing import Dict, List, Optional, Union

from openai import OpenAI

from app.configs.llms.base import BaseLlmConfig
from app.configs.llms.qwen import QWENConfig
from app.services.llms.base import LLMBase
from app.utils.json import extract_json


class QwenLLM(LLMBase):
    def __init__(self, config: Optional[Union[BaseLlmConfig, QWENConfig, Dict]] = None):
        # Convert to QWENConfig if needed
        if config is None:
            config = QWENConfig()
        elif isinstance(config, dict):
            config = QWENConfig(**config)
        elif isinstance(config, BaseLlmConfig) and not isinstance(config, QWENConfig):
            # Convert BaseLlmConfig to QWENConfig
            config = QWENConfig(
                model=config.model,
                temperature=config.temperature,
                api_key=config.api_key,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                top_k=config.top_k,
                enable_vision=config.enable_vision,
                vision_details=config.vision_details,
                http_client_proxies=config.http_client_proxies,
            )

        super().__init__(config)

        if not self.config.model:
            self.config.model = "qwen-turbo"

        api_key = self.config.api_key or os.getenv("DASHSCOPE_API_KEY")
        base_url = self.config.qwen_base_url or os.getenv("QWEN_API_BASE") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def _parse_response(self, response, tools):
        """
        Process the response based on whether tools are used or not.

        Args:
            response: The raw response from API.
            tools: The list of tools provided in the request.

        Returns:
            str or dict: The processed response.
        """
        if tools:
            processed_response = {
                "content": response.choices[0].message.content,
                "tool_calls": [],
            }

            if response.choices[0].message.tool_calls:
                for tool_call in response.choices[0].message.tool_calls:
                    processed_response["tool_calls"].append(
                        {
                            "name": tool_call.function.name,
                            "arguments": json.loads(extract_json(tool_call.function.arguments)),
                        }
                    )

            return processed_response
        else:
            return response.choices[0].message.content

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        response_format=None,
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        **kwargs,
    ):
        """
        Generate a response based on the given messages using Qwen.

        Args:
            messages (list): List of message dicts containing 'role' and 'content'.
            response_format (str or object, optional): Format of the response. Defaults to "text".
            tools (list, optional): List of tools that the model can call. Defaults to None.
            tool_choice (str, optional): Tool choice method. Defaults to "auto".
            **kwargs: Additional Qwen-specific parameters.

        Returns:
            str: The generated response.
        """
        params = self._get_supported_params(messages=messages, **kwargs)
        params.update(
            {
                "model": self.config.model,
                "messages": messages,
            }
        )

        if tools:
            params["tools"] = tools
            params["tool_choice"] = tool_choice

        response = self.client.chat.completions.create(**params)
        return self._parse_response(response, tools)

    def generate_response_stream(
        self,
        messages: List[Dict[str, str]],
        response_format=None,
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        **kwargs,
    ):
        """
        Generate a streaming response based on the given messages using Qwen.

        Args:
            messages (list): List of message dicts containing 'role' and 'content'.
            response_format (str or object, optional): Format of the response. Defaults to "text".
            tools (list, optional): List of tools that the model can call. Defaults to None.
            tool_choice (str, optional): Tool choice method. Defaults to "auto".
            **kwargs: Additional Qwen-specific parameters.

        Yields:
            str: Chunks of the generated response.
        """
        params = self._get_supported_params(messages=messages, **kwargs)
        params.update(
            {
                "model": self.config.model,
                "messages": messages,
                "stream": True,
            }
        )

        if tools:
            params["tools"] = tools
            params["tool_choice"] = tool_choice

        stream = self.client.chat.completions.create(**params)

        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    yield delta.content
