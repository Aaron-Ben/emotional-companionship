"""Diary API endpoints for managing character diary entries."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.services.diary.file_service import DiaryFileService
from app.models.diary import DiaryEntry
from app.models.database import SessionLocal, DiaryFileTable


# Create router
router = APIRouter(prefix="/api/v1/diary", tags=["diary"])


# Pydantic models for request/response
class CreateDiaryRequest(BaseModel):
    """创建日记请求"""
    diary_name: str = Field(..., description="日记本名称（文件夹名）")
    date: str = Field(..., description="日记日期 (YYYY-MM-DD)")
    content: str = Field(..., description="日记内容（应包含末尾的 Tag: xxx, xxx）")
    tag: Optional[str] = Field(None, description="可选标签，将添加到内容末尾")


class UpdateDiaryRequest(BaseModel):
    """更新日记请求"""
    content: str = Field(..., description="日记内容（应包含末尾的 Tag 行）")


class AIUpdateDiaryRequest(BaseModel):
    """AI更新日记请求"""
    target: str = Field(..., min_length=15, description="要查找和替换的旧内容（至少15字符）")
    replace: str = Field(..., description="替换的新内容")
    diary_name: Optional[str] = Field(None, description="日记本名称（可选，用于指定搜索范围）")


class DiaryResponse(BaseModel):
    """日记响应"""
    diary: DiaryEntry
    message: str


# Dependency injection
def get_diary_file_service():
    """获取日记文件服务实例"""
    return DiaryFileService()


@router.get("/list")
async def list_diaries(
    diary_name: Optional[str] = None,
    limit: int = 10,
    diary_service: DiaryFileService = Depends(get_diary_file_service)
):
    """
    获取日记列表

    Query Parameters:
    - diary_name: 可选的日记本名称
    - limit: 返回数量限制 (default: 10)
    """
    try:
        diaries = diary_service.list_diaries(diary_name=diary_name, limit=limit)
        return [DiaryEntry(**d) for d in diaries]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日记列表失败: {str(e)}")


@router.get("/names")
async def list_diary_names(
    diary_service: DiaryFileService = Depends(get_diary_file_service)
):
    """获取所有日记本名称列表"""
    try:
        names = diary_service.list_diary_names()
        return {"names": names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日记本名称失败: {str(e)}")


@router.get("/latest")
async def get_latest_diary(
    diary_name: Optional[str] = None,
    diary_service: DiaryFileService = Depends(get_diary_file_service)
):
    """
    获取最新的日记

    Query Parameters:
    - diary_name: 可选的日记本名称
    """
    try:
        diaries = diary_service.list_diaries(diary_name=diary_name, limit=1)
        if not diaries:
            return None
        return DiaryEntry(**diaries[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取最新日记失败: {str(e)}")


@router.get("/sync")
async def sync_diary_files(
    diary_service: DiaryFileService = Depends(get_diary_file_service)
):
    """同步文件系统到数据库"""
    try:
        result = diary_service.sync_files()
        return {
            "message": "文件同步完成",
            "added": result["added"],
            "updated": result["updated"],
            "removed": result["removed"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件同步失败: {str(e)}")


@router.get("/{path:path}")
async def get_diary_by_path(
    path: str,
    diary_service: DiaryFileService = Depends(get_diary_file_service)
):
    """
    根据路径获取日记详情

    Path Parameters:
    - path: 文件相对路径 (例如: sister_001/2025-01-23_143052.txt)
    """
    try:
        diary = diary_service.read_diary(path)
        if not diary:
            raise HTTPException(status_code=404, detail="日记不存在")
        return DiaryEntry(**diary)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日记失败: {str(e)}")


@router.post("/create")
async def create_diary(
    request: CreateDiaryRequest,
    diary_service: DiaryFileService = Depends(get_diary_file_service)
):
    """
    AI创建日记

    Request Body:
    ```json
    {
        "diary_name": "sister_001",
        "date": "2025-01-23",
        "content": "今天哥哥陪我玩了一整天...\\n\\nTag: 开心, 约会",
        "tag": null
    }
    ```
    """
    try:
        result = diary_service.create_diary(
            diary_name=request.diary_name,
            date=request.date,
            content=request.content,
            tag=request.tag
        )

        if result["status"] == "success":
            return {
                "message": result["message"],
                "diary": DiaryEntry(**result["data"])
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建日记失败: {str(e)}")


@router.post("/ai-update")
async def ai_update_diary(
    request: AIUpdateDiaryRequest,
    diary_service: DiaryFileService = Depends(get_diary_file_service)
):
    """
    AI更新日记

    Request Body:
    ```json
    {
        "target": "这是日记中要被替换掉的旧内容，至少15个字符长",
        "replace": "这是将要写入日记的新内容",
        "diary_name": "sister_001"
    }
    ```

    如果不指定diary_name，会在所有日记本中搜索。
    """
    try:
        result = diary_service.update_diary(
            target=request.target,
            replace=request.replace,
            diary_name=request.diary_name
        )

        if result["status"] == "success":
            return {
                "message": result["message"],
                "path": result["path"],
                "old_content": request.target,
                "new_content": request.replace
            }
        else:
            raise HTTPException(status_code=404, detail=result["message"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新日记失败: {str(e)}")


@router.delete("/{path:path}")
async def delete_diary(
    path: str,
    diary_service: DiaryFileService = Depends(get_diary_file_service)
):
    """
    删除日记

    Path Parameters:
    - path: 文件相对路径

    Returns:
    ```json
    {
        "message": "日记删除成功",
        "path": "sister_001/2025-01-23_143052.txt"
    }
    ```
    """
    try:
        success = diary_service.delete_diary(path)
        if not success:
            raise HTTPException(status_code=404, detail="日记不存在")

        return {
            "message": "日记删除成功",
            "path": path
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除日记失败: {str(e)}")
