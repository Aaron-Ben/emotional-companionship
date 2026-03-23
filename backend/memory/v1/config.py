"""
V1 记忆系统配置
"""

import os
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class MemoryV1Config:
    """V1 记忆系统配置"""

    # 启用状态
    enabled: bool = True

    # 向量索引配置
    dimension: int = 1024
    capacity: int = 50000

    # 标签配置
    tag_blacklist: set = field(default_factory=set)
    tag_expand_max_count: int = 30

    # 去重阈值
    deduplication_threshold: float = 0.88

    # RAG 配置
    rag_modifier: str = "TagMemo0.65"
    rag_k: int = 5

    # EPA 模块配置
    epa_enabled: bool = True

    # 残差金字塔配置
    residual_pyramid_enabled: bool = True
    max_pyramid_levels: int = 3

    # 上下文向量配置
    context_vector_allow_api: bool = False

    @classmethod
    def from_env(cls) -> "MemoryV1Config":
        """从环境变量加载配置"""
        return cls(
            enabled=os.getenv("MEMORY_V1_ENABLED", "true").lower() == "true",
            dimension=int(os.getenv("VECTOR_DIMENSION", "1024")),
            capacity=int(os.getenv("VECTOR_CAPACITY", "50000")),
            rag_modifier=os.getenv("RAG_MODIFIER", "TagMemo0.65"),
            rag_k=int(os.getenv("RAG_K", "5")),
            epa_enabled=os.getenv("EPA_ENABLED", "true").lower() == "true",
            residual_pyramid_enabled=os.getenv("RESIDUAL_PYRAMID_ENABLED", "true").lower() == "true",
            context_vector_allow_api=os.getenv("CONTEXT_VECTOR_ALLOW_API_HISTORY", "false").lower() == "true",
        )
