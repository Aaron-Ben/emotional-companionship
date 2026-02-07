"""File-based diary service for emotional companionship system.

Similar to VCPToolBox DailyNote plugin functionality:
- Diaries are stored as text files in organized folders
- Database tracks file metadata (path, checksum, mtime, size)
- Supports creating, updating, and listing diary files
"""

import hashlib
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.models.database import SessionLocal, DiaryFileTable

logger = logging.getLogger(__name__)


# 默认日记根目录
DEFAULT_DIARY_ROOT = Path(__file__).parent.parent.parent / "data" / "diary"

# 忽略的文件夹列表
IGNORED_FOLDERS = ['MusicDiary']


def get_diary_root() -> Path:
    """获取日记根目录"""
    path_str = os.getenv("DIARY_ROOT_PATH")
    if path_str:
        return Path(path_str)
    return DEFAULT_DIARY_ROOT


def sanitize_path_component(name: str) -> str:
    """清理路径组件，确保安全"""
    if not name or isinstance(name, str):
        name = str(name) if name else "Untitled"

    sanitized = name \
        .replace('\\', '').replace('/', '').replace(':', '') \
        .replace('*', '').replace('?', '').replace('"', '') \
        .replace('<', '').replace('>', '').replace('|', '') \
        .replace('\x00', '').replace('\r', '').replace('\n', '') \
        .strip()

    # 限制长度
    return sanitized[:100] or "Untitled"


def calculate_file_checksum(file_path: Path) -> str:
    """计算文件的 MD5 哈希"""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


class DiaryFileService:
    """基于文件系统的日记服务"""

    TAG_PATTERN = re.compile(r'^Tag:\s*(.+)$', re.MULTILINE | re.IGNORECASE)

    def __init__(self, diary_root: Optional[Path] = None):
        """初始化日记文件服务

        Args:
            diary_root: 日记根目录，默认为 DEFAULT_DIARY_ROOT
        """
        self.diary_root = diary_root or get_diary_root()
        self.diary_root.mkdir(parents=True, exist_ok=True)

    def _ensure_tag_line(self, content: str, tag: Optional[str] = None) -> str:
        """确保内容有 Tag 行"""
        lines = content.split('\n')
        if lines:
            last_line = lines[-1].strip()
            if self.TAG_PATTERN.match(last_line):
                if tag and tag.strip():
                    return '\n'.join(lines[:-1]).rstrip() + f"\n\nTag: {tag.strip()}"
                return content

        if tag and tag.strip():
            return content.rstrip() + f"\n\nTag: {tag.strip()}"

        raise ValueError(
            "Tag is missing. Please provide a 'tag' parameter or add a 'Tag:' line at the end."
        )

    def get_file_path(self, diary_name: str, date: str) -> Path:
        """获取日记文件路径

        Args:
            diary_name: 日记本名称（文件夹名）
            date: 日期 YYYY-MM-DD

        Returns:
            文件路径
        """
        sanitized_name = sanitize_path_component(diary_name)
        date_part = date.replace(".", "-").replace("/", "-").replace("\\", "-").strip()

        # 获取当前时间戳用于唯一文件名
        now = datetime.now()
        time_str = now.strftime("%H_%M_%S")
        filename = f"{date_part}-{time_str}.txt"

        return self.diary_root / sanitized_name / filename

    def create_diary(
        self,
        diary_name: str,
        date: str,
        content: str,
        tag: Optional[str] = None
    ) -> Dict[str, any]:
        """创建日记文件

        Args:
            diary_name: 日记本名称
            date: 日期 YYYY-MM-DD
            content: 日记内容
            tag: 可选标签

        Returns:
            包含文件元数据的字典
        """
        # 检查是否是忽略的文件夹
        sanitized_name = sanitize_path_component(diary_name)
        if sanitized_name in IGNORED_FOLDERS:
            return {
                "status": "error",
                "message": f"Cannot create diary in ignored folder: {sanitized_name}"
            }

        # 确保 Tag 行存在
        content_with_tag = self._ensure_tag_line(content, tag)

        # 获取文件路径
        file_path = self.get_file_path(diary_name, date)

        # 如果文件已存在，添加计数器后缀
        counter = 1
        original_path = file_path
        while file_path.exists():
            stem = original_path.stem
            extension = original_path.suffix
            file_path = original_path.parent / f"{stem}({counter}){extension}"
            counter += 1

        # 创建目录
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        file_path.write_text(content_with_tag, encoding='utf-8')

        # 获取文件元数据
        stat = file_path.stat()
        mtime = int(stat.st_mtime)
        size = stat.st_size
        checksum = calculate_file_checksum(file_path)

        # 保存到数据库
        db = SessionLocal()
        try:
            # 计算相对路径
            relative_path = file_path.relative_to(self.diary_root).as_posix()

            file_record = DiaryFileTable(
                path=relative_path,
                diary_name=sanitized_name,
                checksum=checksum,
                mtime=mtime,
                size=size,
                updated_at=int(datetime.now().timestamp())
            )
            db.add(file_record)
            db.commit()
            db.refresh(file_record)

            logger.info(f"Diary file created: {relative_path}")

            return {
                "status": "success",
                "message": f"Diary saved to {relative_path}",
                "data": {
                    "id": file_record.id,
                    "path": relative_path,
                    "diary_name": sanitized_name,
                    "content": content_with_tag,
                    "mtime": mtime,
                    "size": size
                }
            }
        finally:
            db.close()

    def read_diary(self, path: str) -> Optional[Dict[str, any]]:
        """读取日记文件

        Args:
            path: 文件相对路径

        Returns:
            包含文件内容和元数据的字典，如果文件不存在返回 None
        """
        file_path = self.diary_root / path

        if not file_path.exists():
            return None

        content = file_path.read_text(encoding='utf-8')
        stat = file_path.stat()
        mtime = int(stat.st_mtime)

        # 从路径中提取 diary_name
        diary_name = path.split('/')[0]

        return {
            "path": path,
            "diary_name": diary_name,
            "content": content,
            "mtime": mtime
        }

    def update_diary(
        self,
        target: str,
        replace: str,
        diary_name: Optional[str] = None
    ) -> Dict[str, any]:
        """更新日记文件（查找并替换内容）

        Args:
            target: 要查找的旧内容（至少15字符）
            replace: 替换的新内容
            diary_name: 可选的日记本名称，用于限定搜索范围

        Returns:
            操作结果
        """
        if len(target) < 15:
            return {
                "status": "error",
                "message": f"Security check failed: 'target' must be at least 15 characters. Provided: {len(target)}"
            }

        db = SessionLocal()
        try:
            # 构建查询
            query = db.query(DiaryFileTable)
            if diary_name:
                sanitized_name = sanitize_path_component(diary_name)
                query = query.filter(DiaryFileTable.diary_name == sanitized_name)

            # 按 mtime 降序排列（最新的在前）
            files = query.order_by(DiaryFileTable.mtime.desc()).all()

            for file_record in files:
                file_path = self.diary_root / file_record.path
                if not file_path.exists():
                    continue

                content = file_path.read_text(encoding='utf-8')

                if target in content:
                    # 替换内容
                    new_content = content.replace(target, replace, 1)
                    file_path.write_text(new_content, encoding='utf-8')

                    # 更新元数据
                    stat = file_path.stat()
                    file_record.mtime = int(stat.st_mtime)
                    file_record.size = stat.st_size
                    file_record.checksum = calculate_file_checksum(file_path)
                    file_record.updated_at = int(datetime.now().timestamp())
                    db.commit()

                    logger.info(f"Diary file updated: {file_record.path}")

                    return {
                        "status": "success",
                        "message": f"Successfully edited diary: {file_record.path}",
                        "path": file_record.path
                    }

            char_msg = f" for diary '{diary_name}'" if diary_name else ""
            return {
                "status": "error",
                "message": f"Target content not found in any diary{char_msg}."
            }
        finally:
            db.close()

    def list_diaries(self, diary_name: Optional[str] = None, limit: int = 10) -> List[Dict[str, any]]:
        """列出日记文件

        Args:
            diary_name: 可选的日记本名称
            limit: 返回数量限制

        Returns:
            日记文件列表
        """
        db = SessionLocal()
        try:
            query = db.query(DiaryFileTable)
            if diary_name:
                sanitized_name = sanitize_path_component(diary_name)
                query = query.filter(DiaryFileTable.diary_name == sanitized_name)

            files = query.order_by(DiaryFileTable.mtime.desc()).limit(limit).all()

            result = []
            for file_record in files:
                file_path = self.diary_root / file_record.path
                if file_path.exists():
                    content = file_path.read_text(encoding='utf-8')
                    result.append({
                        "path": file_record.path,
                        "diary_name": file_record.diary_name,
                        "content": content,
                        "mtime": file_record.mtime
                    })

            return result
        finally:
            db.close()

    def list_diary_names(self) -> List[str]:
        """列出所有日记本名称（文件夹名）

        Returns:
            日记本名称列表
        """
        db = SessionLocal()
        try:
            names = db.query(DiaryFileTable.diary_name).distinct().all()
            return [name[0] for name in names if name[0] not in IGNORED_FOLDERS]
        finally:
            db.close()

    def delete_diary(self, path: str) -> bool:
        """删除日记文件

        Args:
            path: 文件相对路径

        Returns:
            是否删除成功
        """
        file_path = self.diary_root / path

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

    def sync_files(self) -> Dict[str, any]:
        """同步文件系统到数据库

        扫描日记目录，添加新文件到数据库，删除不存在的文件记录

        Returns:
            同步结果统计
        """
        added_count = 0
        removed_count = 0
        updated_count = 0

        db = SessionLocal()
        try:
            # 获取数据库中的所有文件
            existing_files = {f.path: f for f in db.query(DiaryFileTable).all()}

            # 扫描文件系统
            for diary_dir in self.diary_root.iterdir():
                if not diary_dir.is_dir():
                    continue

                dir_name = diary_dir.name
                if dir_name in IGNORED_FOLDERS:
                    continue

                for file_path in diary_dir.glob("*.txt"):
                    relative_path = file_path.relative_to(self.diary_root).as_posix()
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
                            record.updated_at = int(datetime.now().timestamp())
                            updated_count += 1
                        del existing_files[relative_path]
                    else:
                        # 添加新记录
                        new_record = DiaryFileTable(
                            path=relative_path,
                            diary_name=dir_name,
                            checksum=checksum,
                            mtime=mtime,
                            size=size,
                            updated_at=int(datetime.now().timestamp())
                        )
                        db.add(new_record)
                        added_count += 1

            # 删除数据库中不存在于文件系统的记录
            for path in existing_files:
                db.query(DiaryFileTable).filter(DiaryFileTable.path == path).delete()
                removed_count += 1

            db.commit()

            logger.info(f"File sync completed: added={added_count}, updated={updated_count}, removed={removed_count}")

            return {
                "added": added_count,
                "updated": updated_count,
                "removed": removed_count
            }
        finally:
            db.close()
