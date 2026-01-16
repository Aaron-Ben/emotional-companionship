from typing import Optional

from app.configs.llms.base import BaseLlmConfig


class QWENConfig(BaseLlmConfig):
    """
    Configuration class for QWEN-specific parameters.
    Inherits from BaseLlmConfig and adds QWEN-specific settings.
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
        # qwen-specific parameters
        qwen_base_url: Optional[str] = None,
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

        # Qwen-specific parameters
        self.qwen_base_url = qwen_base_url
