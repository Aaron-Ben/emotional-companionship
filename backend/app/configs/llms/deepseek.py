from typing import Optional

from app.configs.llms.base import BaseLlmConfig


class DeepSeekConfig(BaseLlmConfig):
    """
    Configuration class for DeepSeek-specific parameters.
    Inherits from BaseLlmConfig and adds DeepSeek-specific settings.
    """

    def __init__(
        self,
        # Base parameters
        model: Optional[str] = None,
        temperature: float = 0.1,
        api_key: Optional[str] = None,
        max_tokens: int = 2000,
        top_p: float = 0.1,
        top_k: int = 1,
        enable_vision: bool = False,
        vision_details: Optional[str] = "auto",
        http_client_proxies: Optional[dict] = None,
        # DeepSeek-specific parameters
        deepseek_base_url: Optional[str] = None,
    ):
        # Initialize base parameters
        super().__init__(
            model=model,
            temperature=temperature,
            api_key=api_key,
            max_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
            enable_vision=enable_vision,
            vision_details=vision_details,
            http_client_proxies=http_client_proxies,
        )

        # DeepSeek-specific parameters
        self.deepseek_base_url = deepseek_base_url
