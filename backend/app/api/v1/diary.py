"""Diary API endpoints for managing character diary entries."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.services.diary import DiaryCoreService
from app.services.diary.ai_service import AIDiaryService
from app.models.diary import DiaryEntry
from app.models.database import SessionLocal, DiaryTable


# Create router
router = APIRouter(prefix="/api/v1/diary", tags=["diary"])


# Pydantic models for request/response
class UpdateDiaryRequest(BaseModel):
    """更新日记请求"""
    content: str = Field(..., description="日记内容")
    tags: List[str] = Field(default_factory=list, description="标签列表")


class AICreateDiaryRequest(BaseModel):
    """AI创建日记请求"""
    character_id: str = Field(..., description="角色ID")
    date: str = Field(..., description="日记日期 (YYYY-MM-DD)")
    content: str = Field(..., description="日记内容（支持在末尾添加 Tag: xxx, xxx）")
    category: str = Field(default="topic", description="日记分类: knowledge/topic/milestone")
    tag: Optional[str] = Field(None, description="独立标签字段（如果提供，将覆盖content中的Tag行）")


class AIUpdateDiaryRequest(BaseModel):
    """AI更新日记请求"""
    target: str = Field(..., min_length=15, description="要查找和替换的旧内容（至少15字符）")
    replace: str = Field(..., description="替换的新内容")
    character_id: Optional[str] = Field(None, description="角色ID（可选，用于指定搜索范围）")


class DiaryResponse(BaseModel):
    """日记响应"""
    diary: DiaryEntry
    message: str


# Dependency injection
def get_diary_core_service():
    """获取日记核心服务实例"""
    return DiaryCoreService()


def get_mock_user_id():
    """获取模拟用户ID"""
    return "user_default"


@router.get("/list", response_model=List[DiaryEntry])
async def list_diaries(
    character_id: str,
    user_id: str = Depends(get_mock_user_id),
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
                    category=db_diary.category,
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
    diary_service: DiaryCoreService = Depends(get_diary_core_service)
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
    user_id: str = Depends(get_mock_user_id)
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
                category=db_diary.category,
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
                category=db_diary.category,
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
    user_id: str = Depends(get_mock_user_id)
):
    """
    更新日记内容

    Path Parameters:
    - diary_id: 日记ID

    Request Body:
    ```json
    {
        "content": "更新后的日记内容",
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
            db_diary.tags = request.tags
            db_diary.updated_at = datetime.now()

            db.commit()
            db.refresh(db_diary)

            diary_entry = DiaryEntry(
                id=db_diary.id,
                character_id=db_diary.character_id,
                user_id=db_diary.user_id,
                date=db_diary.date,
                content=db_diary.content,
                category=db_diary.category,
                emotions=db_diary.emotions,
                tags=db_diary.tags,
                created_at=db_diary.created_at,
                updated_at=db_diary.updated_at
            )

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
    user_id: str = Depends(get_mock_user_id)
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

            # 删除数据库记录（SQLite only, no file system）
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


@router.post("/ai-create", response_model=DiaryResponse)
async def ai_create_diary(
    request: AICreateDiaryRequest,
    user_id: str = Depends(get_mock_user_id)
):
    """
    AI创建日记

    类似VCPToolBox DailyNote的create命令，允许AI主动创建日记。

    Request Body:
    ```json
    {
        "character_id": "sister_001",
        "date": "2025-01-23",
        "content": "今天哥哥陪我玩了一整天，我们去了公园...",
        "category": "milestone",
        "tag": "开心, 约会, 温暖"
    }
    ```

    或者将标签放在内容末尾：
    ```json
    {
        "character_id": "sister_001",
        "date": "2025-01-23",
        "content": "今天哥哥陪我玩了一整天...\\n\\nTag: 开心, 约会"
    }
    ```
    """
    try:
        ai_service = AIDiaryService()
        diary_entry = await ai_service.create_diary(
            character_id=request.character_id,
            user_id=user_id,
            date=request.date,
            content=request.content,
            category=request.category,
            tag=request.tag
        )

        return DiaryResponse(
            diary=diary_entry,
            message="日记创建成功"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建日记失败: {str(e)}")


@router.post("/ai-update")
async def ai_update_diary(
    request: AIUpdateDiaryRequest,
    user_id: str = Depends(get_mock_user_id)
):
    """
    AI更新日记

    类似VCPToolBox DailyNote的update命令，通过查找和替换内容来更新日记。

    Request Body:
    ```json
    {
        "target": "这是日记中要被替换掉的旧内容，至少15个字符长",
        "replace": "这是将要写入日记的新内容",
        "character_id": "sister_001"
    }
    ```

    如果不指定character_id，会在所有角色的日记中搜索。
    """
    try:
        ai_service = AIDiaryService()
        result = await ai_service.update_diary(
            target=request.target,
            replace=request.replace,
            user_id=user_id,
            character_id=request.character_id
        )

        if result["status"] == "success":
            return {
                "message": result["message"],
                "diary_id": result.get("diary_id"),
                "old_content": request.target,
                "new_content": request.replace
            }
        else:
            raise HTTPException(status_code=404, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新日记失败: {str(e)}")
