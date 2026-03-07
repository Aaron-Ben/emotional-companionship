"""File-based diary service for emotional companionship system.

Diaries are now stored in data/daily/{name}/
- Global diary directory organized by character name
- Database tracks file metadata (path, checksum, mtime, size)
- Supports reading, listing, and deleting diary files
- Creating and updating diaries is now handled by the DailyNote plugin
"""

import hashlib
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from app.models.database import SessionLocal, DiaryFileTable
from app.services.character_service import CharacterService

logger = logging.getLogger(__name__)


# 默认目录
DEFAULT_CHARACTERS_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "characters"
DEFAULT_DAILY_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "daily"


def get_characters_dir() -> Path:
    """获取角色目录"""
    path_str = os.getenv("CHARACTERS_DIR")
    if path_str:
        return Path(path_str)
    return DEFAULT_CHARACTERS_DIR


def get_daily_dir() -> Path:
    """获取全局日记目录"""
    path_str = os.getenv("DAILY_DIR")
    if path_str:
        return Path(path_str)
    return DEFAULT_DAILY_DIR


def calculate_file_checksum(file_path: Path) -> str:
    """计算文件的 MD5 哈希"""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


class DiaryFileService:
    """基于文件系统的日记服务（只读操作）

    日记保存在 data/daily/{name}/ 目录下
    创建和更新日记由 DailyNote 插件处理
    """

    def __init__(self, characters_dir: Optional[Path] = None, daily_dir: Optional[Path] = None):
        """初始化日记文件服务

        Args:
            characters_dir: 角色根目录，默认为 DEFAULT_CHARACTERS_DIR
            daily_dir: 全局日记根目录，默认为 DEFAULT_DAILY_DIR
        """
        self.characters_dir = characters_dir or get_characters_dir()
        self.characters_dir.mkdir(parents=True, exist_ok=True)
        self.daily_dir = daily_dir or get_daily_dir()
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        self.character_service = CharacterService(self.characters_dir, self.daily_dir)

    def read_diary(self, path: str) -> Optional[Dict[str, any]]:
        """读取日记文件

        Args:
            path: 文件相对路径 (格式: {name}/{filename}.txt)

        Returns:
            包含文件内容和元数据的字典，如果文件不存在返回 None
        """
        file_path = self.daily_dir / path

        if not file_path.exists():
            return None

        content = file_path.read_text(encoding='utf-8')
        stat = file_path.stat()
        mtime = int(stat.st_mtime)

        # 从路径中提取 name (第一个路径组件)
        path_parts = path.split('/')
        name = path_parts[0] if path_parts else ""

        return {
            "path": path,
            "character_id": name,  # 使用 name 作为 character_id
            "content": content,
            "mtime": mtime
        }

    def list_diaries(self, character_id: str, limit: int = 10) -> List[Dict[str, any]]:
        """列出指定角色的日记文件

        Args:
            character_id: 角色 ID (UUID)
            limit: 返回数量限制

        Returns:
            日记文件列表
        """
        # 获取角色信息，获取 name
        character = self.character_service.get_character(character_id)
        if not character:
            return []

        name = self._sanitize_name(character.name)
        name_daily_dir = self.daily_dir / name

        db = SessionLocal()
        try:
            files = (db.query(DiaryFileTable)
                    .filter(DiaryFileTable.diary_name == name)
                    .order_by(DiaryFileTable.mtime.desc())
                    .limit(limit)
                    .all())

            result = []
            for file_record in files:
                file_path = self.daily_dir / file_record.path
                if file_path.exists():
                    content = file_path.read_text(encoding='utf-8')
                    result.append({
                        "path": file_record.path,
                        "character_id": character_id,
                        "content": content,
                        "mtime": file_record.mtime
                    })
            if result:
                return result
            
            if name_daily_dir.exists():
                for file_path in sorted(name_daily_dir.glob("*.txt"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:   
                    try:                                                                                                        
                        content = file_path.read_text(encoding='utf-8')                                                         
                        relative_path = file_path.relative_to(self.daily_dir).as_posix()                                        
                        stat = file_path.stat()                                                                                 
                        result.append({                                                                                         
                           "path": relative_path,                                                                              
                            "character_id": character_id,                                                                       
                            "content": content,                                                                                 
                           "mtime": int(stat.st_mtime)                                                                         
                        })                                                                                                      
                    except Exception:                                                                                           
                        continue  

            return result
        
        finally:
            db.close()

    def _sanitize_name(self, name: str) -> str:
        """清理角色名称作为目录名"""
        import re
        sanitized = re.sub(r'[\\/:*?"<>|]', '', name.strip())
        sanitized = re.sub(r'\s+', '_', sanitized)
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        return sanitized or 'unnamed'

    def list_all_diary_names(self) -> List[str]:
        """列出所有有日记的角色ID列表

        Returns:
            角色 ID 列表
        """
        db = SessionLocal()
        try:
            names = db.query(DiaryFileTable.diary_name).distinct().all()
            return [name[0] for name in names]
        finally:
            db.close()

    def delete_diary(self, path: str) -> bool:
        """删除日记文件

        Args:
            path: 文件相对路径 (格式: {name}/{filename}.txt)

        Returns:
            是否删除成功
        """
        file_path = self.daily_dir / path

        db = SessionLocal()
        try:
            # 删除数据库记录
            db.query(DiaryFileTable).filter(DiaryFileTable.path == path).delete()
            db.commit()

            # 删除文件
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Diary file deleted: {path}")
                return True

            return False
        finally:
            db.close()

    def update_file_metadata(self, character_id: str) -> Dict[str, any]:
        """更新指定角色的日记文件元数据到数据库

        扫描角色的日记目录，添加新文件到数据库，删除不存在的文件记录

        Args:
            character_id: 角色 ID (UUID)

        Returns:
            更新结果统计 {added, updated, removed}
        """
        added_count = 0
        removed_count = 0
        updated_count = 0

        # 获取角色信息，获取 name
        character = self.character_service.get_character(character_id)
        if not character:
            return {
                "character_id": character_id,
                "added": 0,
                "updated": 0,
                "removed": 0,
                "error": "Character not found"
            }

        name = self._sanitize_name(character.name)
        daily_dir = self.daily_dir / name

        db = SessionLocal()
        try:
            # 获取该角色的所有文件
            existing_files = {
                f.path: f
                for f in db.query(DiaryFileTable)
                       .filter(DiaryFileTable.diary_name == name)
                       .all()
            }

            # 扫描文件系统
            if daily_dir.exists():
                for file_path in daily_dir.glob("*.txt"):
                    relative_path = file_path.relative_to(self.daily_dir).as_posix()
                    stat = file_path.stat()
                    mtime = int(stat.st_mtime)
                    size = stat.st_size
                    checksum = calculate_file_checksum(file_path)

                    if relative_path in existing_files:
                        # 更新现有记录
                        record = existing_files[relative_path]
                        if (record.checksum != checksum or
                            record.mtime != mtime or
                            record.size != size):
                            record.checksum = checksum
                            record.mtime = mtime
                            record.size = size
                            record.updated_at = int(__import__('datetime').datetime.now().timestamp())
                            updated_count += 1
                        del existing_files[relative_path]
                    else:
                        # 添加新记录
                        new_record = DiaryFileTable(
                            path=relative_path,
                            diary_name=name,
                            checksum=checksum,
                            mtime=mtime,
                            size=size,
                            updated_at=int(__import__('datetime').datetime.now().timestamp())
                        )
                        db.add(new_record)
                        added_count += 1

            # 删除数据库中不存在于文件系统的记录
            for path in existing_files:
                db.query(DiaryFileTable).filter(DiaryFileTable.path == path).delete()
                removed_count += 1

            db.commit()

            logger.info(f"Character {character_id} file metadata update completed: added={added_count}, updated={updated_count}, removed={removed_count}")

            return {
                "character_id": character_id,
                "added": added_count,
                "updated": updated_count,
                "removed": removed_count
            }
        finally:
            db.close()
