"""
Memory 模块 - 记忆系统

V1: 日记格式 (Diary-based)
V2: 会话格式 (Session-based) - 开发中
"""

import os

# 记忆系统后端配置
MEMORY_BACKEND = os.getenv("MEMORY", "v1")  # 默认 v1
V1_ENABLED = MEMORY_BACKEND == "v1"
V2_ENABLED = MEMORY_BACKEND == "v2"

__all__ = ["MEMORY_BACKEND", "V1_ENABLED", "V2_ENABLED"]
