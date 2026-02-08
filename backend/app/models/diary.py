"""Diary data models for emotional companionship system."""

from pydantic import BaseModel, Field


class DiaryEntry(BaseModel):
    """日记条目数据模型"""
    path: str = Field(..., description="文件相对路径")
    diary_name: str = Field(..., description="日记本名称")
    content: str = Field(..., description="日记内容（第一人称，包含末尾的Tag行）")
    mtime: int = Field(..., description="文件修改时间戳")
