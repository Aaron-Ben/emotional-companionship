"""Diary API endpoints for managing character diary entries."""

from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.services.diary import DiaryService
from app.services.llms.qwen import QwenLLM
from app.models.diary import DiaryEntry, DiaryTriggerType
from app.models.database import SessionLocal, DiaryTable


# Create router
router = APIRouter(prefix="/api/v1/diary", tags=["diary"])


# Pydantic models for request/response
class GenerateDiaryRequest(BaseModel):
    """生成日记请求"""
    character_id: str = Field(..., description="角色ID")
    conversation_summary: str = Field(..., description="对话摘要")
    trigger_type: DiaryTriggerType = Field(..., description="触发类型")
    emotions: List[str] = Field(default_factory=list, description="情绪列表")


class UpdateDiaryRequest(BaseModel):
    """更新日记请求"""
    content: str = Field(..., description="日记内容")
    emotions: List[str] = Field(default_factory=list, description="情绪列表")
    tags: List[str] = Field(default_factory=list, description="标签列表")


class DiaryResponse(BaseModel):
    """日记响应"""
    diary: DiaryEntry
    message: str


# Dependency injection
def get_diary_service():
    """获取日记服务实例"""
    return DiaryService()


def get_llm_service():
    """获取LLM服务实例"""
    return QwenLLM()


def get_mock_user_id():
    """获取模拟用户ID"""
    return "user_default"


@router.post("/generate", response_model=DiaryResponse)
async def generate_diary(
    request: GenerateDiaryRequest,
    user_id: str = Depends(get_mock_user_id),
    diary_service: DiaryService = Depends(get_diary_service),
    llm = Depends(get_llm_service)
):
    """
    手动生成日记

    用于测试或手动触发日记生成

    Request Body:
    ```json
    {
        "character_id": "sister_001",
        "conversation_summary": "今天哥哥跟我说他涨工资了...",
        "trigger_type": "important_event",
        "emotions": ["happy", "excited"]
    }
    ```
    """
    try:
        diary = await diary_service.generate_diary(
            llm=llm,
            character_id=request.character_id,
            user_id=user_id,
            conversation_summary=request.conversation_summary,
            trigger_type=request.trigger_type,
            emotions=request.emotions,
            context={}
        )

        return DiaryResponse(
            diary=diary,
            message="日记生成成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成日记失败: {str(e)}")


@router.get("/list", response_model=List[DiaryEntry])
async def list_diaries(
    character_id: str,
    user_id: str = Depends(get_mock_user_id),
    diary_service: DiaryService = Depends(get_diary_service),
    limit: int = 10
):
    """
    获取日记列表

    返回指定角色的最近日记

    Query Parameters:
    - character_id: 角色ID
    - limit: 返回数量限制 (default: 10)
    """
    try:
        db = SessionLocal()
        try:
            diaries = db.query(DiaryTable).filter(
                DiaryTable.character_id == character_id,
                DiaryTable.user_id == user_id
            ).order_by(DiaryTable.created_at.desc()).limit(limit).all()

            result = []
            for db_diary in diaries:
                result.append(DiaryEntry(
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
                ))

            return result
        finally:
            db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日记列表失败: {str(e)}")


@router.get("/relevant", response_model=List[DiaryEntry])
async def get_relevant_diaries(
    character_id: str,
    message: str,
    user_id: str = Depends(get_mock_user_id),
    diary_service: DiaryService = Depends(get_diary_service)
):
    """
    获取与当前消息相关的日记

    用于在对话时提供上下文

    Query Parameters:
    - character_id: 角色ID
    - message: 当前用户消息
    """
    try:
        relevant_diaries = await diary_service.get_relevant_diaries(
            character_id=character_id,
            user_id=user_id,
            current_message=message,
            limit=5
        )
        return relevant_diaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取相关日记失败: {str(e)}")


@router.get("/latest", response_model=Optional[DiaryEntry])
async def get_latest_diary(
    character_id: str,
    user_id: str = Depends(get_mock_user_id),
    diary_service: DiaryService = Depends(get_diary_service)
):
    """
    获取最新的日记

    Query Parameters:
    - character_id: 角色ID
    """
    try:
        db = SessionLocal()
        try:
            db_diary = db.query(DiaryTable).filter(
                DiaryTable.character_id == character_id,
                DiaryTable.user_id == user_id
            ).order_by(DiaryTable.created_at.desc()).first()

            if not db_diary:
                return None

            return DiaryEntry(
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
        finally:
            db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取最新日记失败: {str(e)}")


@router.get("/{diary_id}", response_model=DiaryEntry)
async def get_diary_by_id(
    diary_id: str,
    user_id: str = Depends(get_mock_user_id)
):
    """
    根据ID获取日记详情

    Path Parameters:
    - diary_id: 日记ID
    """
    try:
        db = SessionLocal()
        try:
            db_diary = db.query(DiaryTable).filter(
                DiaryTable.id == diary_id,
                DiaryTable.user_id == user_id
            ).first()

            if not db_diary:
                raise HTTPException(status_code=404, detail="日记不存在")

            return DiaryEntry(
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
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日记失败: {str(e)}")


@router.put("/{diary_id}", response_model=DiaryResponse)
async def update_diary(
    diary_id: str,
    request: UpdateDiaryRequest,
    user_id: str = Depends(get_mock_user_id),
    diary_service: DiaryService = Depends(get_diary_service)
):
    """
    更新日记内容

    Path Parameters:
    - diary_id: 日记ID

    Request Body:
    ```json
    {
        "content": "更新后的日记内容",
        "emotions": ["开心", "温暖"],
        "tags": ["日常", "开心"]
    }
    ```
    """
    try:
        db = SessionLocal()
        try:
            # 查找日记
            db_diary = db.query(DiaryTable).filter(
                DiaryTable.id == diary_id,
                DiaryTable.user_id == user_id
            ).first()

            if not db_diary:
                raise HTTPException(status_code=404, detail="日记不存在")

            # 更新数据库记录
            db_diary.content = request.content
            db_diary.emotions = request.emotions
            db_diary.tags = request.tags

            from datetime import datetime
            db_diary.updated_at = datetime.now()

            db.commit()
            db.refresh(db_diary)

            # 只更新文件（数据库已经更新过了）
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

            diary_service._update_diary_file(diary_entry)

            return DiaryResponse(
                diary=diary_entry,
                message="日记更新成功"
            )
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新日记失败: {str(e)}")


@router.delete("/{diary_id}")
async def delete_diary(
    diary_id: str,
    user_id: str = Depends(get_mock_user_id),
    diary_service: DiaryService = Depends(get_diary_service)
):
    """
    删除日记

    Path Parameters:
    - diary_id: 日记ID

    Returns:
    ```json
    {
        "message": "日记删除成功",
        "diary_id": "diary_sister_001_user_default_20250116_123456"
    }
    ```
    """
    try:
        db = SessionLocal()
        try:
            # 查找日记
            db_diary = db.query(DiaryTable).filter(
                DiaryTable.id == diary_id,
                DiaryTable.user_id == user_id
            ).first()

            if not db_diary:
                raise HTTPException(status_code=404, detail="日记不存在")

            # 删除文件
            file_path = diary_service._get_diary_file_path(
                db_diary.character_id,
                db_diary.user_id,
                db_diary.date
            )

            if file_path.exists():
                file_path.unlink()

            # 删除数据库记录
            db.delete(db_diary)
            db.commit()

            return {
                "message": "日记删除成功",
                "diary_id": diary_id
            }
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除日记失败: {str(e)}")
