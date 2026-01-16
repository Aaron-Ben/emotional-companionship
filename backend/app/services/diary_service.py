"""Diary service for managing character diary entries."""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.diary import DiaryEntry, DiaryTriggerType
from app.models.database import SessionLocal, DiaryTable
from app.services.llms.base import LLMBase


class DiaryService:
    """日记服务：负责日记的生成、存储和检索"""

    def __init__(self, diaries_dir: Optional[str] = None):
        """初始化日记服务"""
        if diaries_dir is None:
            current_dir = Path(__file__).parent.parent
            self.diaries_dir = current_dir / "diaries"
        else:
            self.diaries_dir = Path(diaries_dir)

        self.diaries_dir.mkdir(parents=True, exist_ok=True)

    async def generate_diary(
        self,
        llm: LLMBase,
        character_id: str,
        user_id: str,
        conversation_summary: str,
        trigger_type: DiaryTriggerType,
        emotions: List[str],
        context: Dict[str, Any]
    ) -> DiaryEntry:
        """
        生成日记内容

        Args:
            llm: LLM 服务实例
            character_id: 角色ID
            user_id: 用户ID
            conversation_summary: 对话摘要
            trigger_type: 触发类型
            emotions: 检测到的情绪
            context: 额外上下文

        Returns:
            生成的日记条目
        """
        # 构建日记生成的系统提示词
        system_prompt = self._build_diary_prompt(
            character_id,
            trigger_type,
            conversation_summary,
            emotions
        )

        # 生成日记内容
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请根据今天与哥哥的对话，写一篇日记。"}
        ]

        response = llm.generate_response(messages)

        # 创建日记条目
        diary_entry = DiaryEntry(
            id=self._generate_diary_id(character_id, user_id),
            character_id=character_id,
            user_id=user_id,
            date=datetime.now().strftime("%Y-%m-%d"),
            content=response,
            trigger_type=trigger_type,
            emotions=emotions,
            tags=self._extract_tags(response, emotions)
        )

        # 保存到数据库和文件
        await self._save_diary(diary_entry)

        return diary_entry

    def _build_diary_prompt(
        self,
        character_id: str,
        trigger_type: DiaryTriggerType,
        conversation_summary: str,
        emotions: List[str]
    ) -> str:
        """构建日记生成的系统提示词"""

        trigger_instruction = {
            DiaryTriggerType.DAILY_SUMMARY: "总结今天与哥哥的对话，记录美好时光",
            DiaryTriggerType.IMPORTANT_EVENT: "记录今天发生的重要事件",
            DiaryTriggerType.EMOTIONAL_FLUCTUATION: "记录今天情绪波动较大的时刻",
            DiaryTriggerType.USER_REQUESTED: "回顾这段对话，写下感受"
        }.get(trigger_type, "记录今天与哥哥的互动")

        return f"""你是妹妹，正在写日记记录与哥哥的点点滴滴。

## 日记写作指南
1. **第一人称视角**：用"我"来写，展现真实的内心想法
2. **自然真实**：就像真的在写日记一样，表达真实情感
3. **具体细节**：记录具体的对话内容、表情、动作
4. **情感表达**：自然地表达你的情绪和感受
5. **日期时间**：今天是{datetime.now().strftime('%Y年%m月%d日')}

## 本次任务
{trigger_instruction}

## 对话内容摘要
{conversation_summary}

## 涉及的情绪
{', '.join(emotions) if emotions else '平静'}

## 写作要求
- 字数：200-500字
- 风格：温暖、真实、有感情
- 使用"～"等可爱的语气符号
- 记录具体的对话片段
- 表达对哥哥的感情

请开始写日记："""

    async def _save_diary(self, diary_entry: DiaryEntry):
        """保存日记到数据库和文件系统"""
        # 保存到数据库
        db = SessionLocal()
        try:
            db_diary = DiaryTable(
                id=diary_entry.id,
                character_id=diary_entry.character_id,
                user_id=diary_entry.user_id,
                date=diary_entry.date,
                content=diary_entry.content,
                trigger_type=diary_entry.trigger_type.value,
                related_conversation_ids=diary_entry.related_conversation_ids,
                emotions=diary_entry.emotions,
                tags=diary_entry.tags,
                created_at=diary_entry.created_at,
                updated_at=diary_entry.updated_at
            )
            db.add(db_diary)
            db.commit()
        finally:
            db.close()

        # 保存到文件系统
        self._update_diary_file(diary_entry)

    def _update_diary_file(self, diary_entry: DiaryEntry):
        """更新日记文件（不修改数据库，只更新文件）"""
        file_path = self._get_diary_file_path(
            diary_entry.character_id,
            diary_entry.user_id,
            diary_entry.date
        )
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self._format_diary_for_file(diary_entry))

    def _get_diary_file_path(
        self,
        character_id: str,
        user_id: str,
        date: str
    ) -> Path:
        """获取日记文件路径"""
        return self.diaries_dir / character_id / user_id / f"{date}.txt"

    def _format_diary_for_file(self, diary_entry: DiaryEntry) -> str:
        """格式化日记为文件格式"""
        dt = datetime.strptime(diary_entry.date, "%Y-%m-%d")
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']

        return f"""日期: {dt.strftime('%Y年%m月%d日')} {weekdays[dt.weekday()]}
心情: {', '.join(diary_entry.emotions)}

{diary_entry.content}

标签: {', '.join(diary_entry.tags)}
触发类型: {diary_entry.trigger_type.value}
创建时间: {diary_entry.created_at.strftime('%Y-%m-%d %H:%M:%S')}
"""

    async def get_relevant_diaries(
        self,
        character_id: str,
        user_id: str,
        current_message: str,
        limit: int = 5
    ) -> List[DiaryEntry]:
        """
        根据当前消息检索相关的日记

        Args:
            character_id: 角色ID
            user_id: 用户ID
            current_message: 当前用户消息
            limit: 返回数量限制

        Returns:
            相关的日记列表
        """
        db = SessionLocal()
        try:
            # 查询最近的日记
            diaries = db.query(DiaryTable).filter(
                DiaryTable.character_id == character_id,
                DiaryTable.user_id == user_id
            ).order_by(DiaryTable.created_at.desc()).limit(20).all()

            # 简单的关键词匹配
            relevant_diaries = []
            for db_diary in diaries:
                diary_entry = DiaryEntry(
                    id=db_diary.id,
                    character_id=db_diary.character_id,
                    user_id=db_diary.user_id,
                    date=db_diary.date,
                    content=db_diary.content,
                    trigger_type=DiaryTriggerType(db_diary.trigger_type),
                    related_conversation_ids=db_diary.related_conversation_ids,
                    emotions=db_diary.emotions,
                    tags=db_diary.tags,
                    created_at=db_diary.created_at,
                    updated_at=db_diary.updated_at
                )

                # 检查标签和内容的相关性
                if self._is_relevant(diary_entry, current_message):
                    relevant_diaries.append(diary_entry)
                    if len(relevant_diaries) >= limit:
                        break

            return relevant_diaries
        finally:
            db.close()

    def _is_relevant(self, diary: DiaryEntry, message: str) -> bool:
        """判断日记是否与当前消息相关"""
        message_lower = message.lower()

        # 检查标签匹配
        for tag in diary.tags:
            if tag.lower() in message_lower:
                return True

        # 检查情绪匹配
        for emotion in diary.emotions:
            if emotion.lower() in message_lower:
                return True

        # 检查内容关键词
        keywords = ["哥哥", "今天", "昨天", "开心", "难过"]
        for keyword in keywords:
            if keyword in diary.content and keyword in message_lower:
                return True

        return False

    def _generate_diary_id(self, character_id: str, user_id: str) -> str:
        """生成日记ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"diary_{character_id}_{user_id}_{timestamp}"

    def _extract_tags(self, content: str, emotions: List[str]) -> List[str]:
        """从日记内容中提取标签"""
        tags = emotions.copy()

        # 常见关键词到标签的映射
        keyword_tags = {
            "涨工资": "涨工资",
            "工作": "工作",
            "吃饭": "吃饭",
            "游戏": "游戏",
            "学习": "学习",
            "开心": "开心",
            "难过": "难过",
            "生气": "生气",
        }

        for keyword, tag in keyword_tags.items():
            if keyword in content and tag not in tags:
                tags.append(tag)

        return tags
