"""Diary data models for emotional companionship system."""

from pydantic import BaseModel, Field


class DiaryEntry(BaseModel):
    """日记条目数据模型"""
    path: str = Field(..., description="文件相对路径")
    diary_name: str = Field(..., description="日记本名称")
    content: str = Field(..., description="日记内容（第一人称，包含末尾的Tag行）")
    mtime: int = Field(..., description="文件修改时间戳")

    class Config:
        json_schema_extra = {
            "example": {
                "path": "sister_001/2025-01-23_143052.txt",
                "diary_name": "sister_001",
                "content": "【对话主题】今天哥哥陪我玩了一整天\n\n【对话记录】\n哥哥：...\n我：...\n\n【我的感受】\n好开心！\n\nTag: 开心, 约会, 温暖",
                "mtime": 1706979452
            }
        }
