"""Vector Index 兼容重定向

此模块已迁移到 memory.v1.vector_index
为保持兼容性，此处重定向导入
"""

import asyncio
import logging
from typing import Dict

from memory.v1.vector_index import (
    VectorIndex as _VectorIndex,
    VectorIndexConfig as _VectorIndexConfig,
    initialize_vector_index as _initialize_vector_index,
    SearchResult as _SearchResult,
    TagBoostResult as _TagBoostResult,
    get_vector_index as _get_vector_index,
)

# 重新导出
VectorIndex = _VectorIndex
VectorIndexConfig = _VectorIndexConfig
initialize_vector_index = _initialize_vector_index
SearchResult = _SearchResult
TagBoostResult = _TagBoostResult
get_vector_index = _get_vector_index


# 需要从 memory.v1.vector_index 导入的函数
async def sync_all_diaries_to_vector_index():
    """同步所有日记到向量索引"""
    from memory.v1.vector_index import sync_all_diaries_to_vector_index as _sync
    return await _sync()


async def sync_character_diary_to_vector_index(character_id: str):
    """同步指定角色的日记到向量索引"""
    from memory.v1.vector_index import sync_character_diary_to_vector_index as _sync_char
    return await _sync_char(character_id)


__all__ = [
    "VectorIndex",
    "VectorIndexConfig",
    "initialize_vector_index",
    "SearchResult",
    "TagBoostResult",
    "get_vector_index",
    "sync_all_diaries_to_vector_index",
    "sync_character_diary_to_vector_index",
]
