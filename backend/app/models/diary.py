"""Diary data models for emotional companionship system."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class DiaryEntry(BaseModel):
    """日记条目数据模型"""
    id: str = Field(..., description="日记唯一ID")
    character_id: str = Field(..., description="角色ID")
    user_id: str = Field(..., description="用户ID")
    date: str = Field(..., description="日记日期 (YYYY-MM-DD)")
    content: str = Field(..., description="日记内容（第一人称）")
    category: str = Field(..., description="日记分类: knowledge/topic/milestone")
    tags: List[str] = Field(default_factory=list, description="标签（如：开心、难过、重要）")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "diary_20250116_001",
                "character_id": "sister_001",
                "user_id": "user_default",
                "date": "2025-01-16",
                "content": "今天哥哥跟我说他涨工资了，看到他那么开心我也好高兴！...",
                "category": "milestone",
                "tags": ["涨工资", "开心", "庆祝"]
            }
        }
