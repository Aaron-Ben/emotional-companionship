import hashlib
import asyncio
import struct
import json
import time
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass
import logging

# ==================== Database ====================
from sqlalchemy.orm import Session
from app.models.database import DiaryFileTable, ChunkTable, SessionLocal

# ==================== Services ====================
from app.services.chunk_text import chunk_text
from app.services.embedding import EmbeddingService
from app.services.character_service import CharacterService

# ==================== 配置 ====================
@dataclass
class VectorIndexConfig:

    """向量索引配置"""
    dimension: int = 1024           # 向量维度
    capacity: int = 50000           # 索引容量
    index_save_delay: float = 5.0   # 保存延迟(秒)

    @property
    def store_path(self) -> Path:
        """获取VectorStore目录路径（项目根目录）"""
        # 从 backend/app/ 向上两级到达项目根目录
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
        return project_root / "VectorStore"


# ==================== VexusIndex 导入 ====================
from vector_db import VexusIndex

# ==================== 核心管理类 ====================
class VectorIndex:
    """简单的向量索引管理器"""

    def __init__(self, config: VectorIndexConfig):
        self.config = config
        self.diary_indices: Dict[str, VexusIndex] = {}  # diaryName -> VexusIndex实例
        self.save_tasks: Dict[str, Optional[asyncio.Task]] = {}  # diaryName -> asyncio.Task
        self._ensure_store_path()

    def _ensure_store_path(self) -> None:
        """确保存储目录存在"""
        store_path = self.config.store_path
        if not store_path.exists():
            store_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"[VectorIndex] Created store path: {store_path}")

    # ==================== 1. 懒加载触发 ====================
    async def _get_or_load_diary_index(self, diary_name: str) -> VexusIndex:
        """
        获取或加载指定日记本的索引（懒加载）

        Args:
            diary_name: 日记本名称，如 "反思簇"

        Returns:
            索引实例
        """
        # 如果已加载，直接返回
        if diary_name in self.diary_indices:
            logging.info(f"[VectorIndex] Cache hit for diary: \"{diary_name}\"")
            return self.diary_indices[diary_name]

        logging.info(f"[VectorIndex] 🔍 Lazy loading index for diary: \"{diary_name}\"")

        # 计算文件名：index_diary_{MD5}.usearch
        safe_name = hashlib.md5(diary_name.encode()).hexdigest()
        idx_name = f"diary_{safe_name}"

        # 加载或创建索引
        idx = await self._load_or_build_index(idx_name, "chunks", diary_name)

        # 缓存索引
        self.diary_indices[diary_name] = idx
        return idx

    # ==================== 2. 加载或创建索引 ====================
    async def _load_or_build_index(
        self,
        file_name: str,
        table_type: str,
        filter_diary_name: Optional[str] = None
    ) -> VexusIndex:
        """
        从磁盘加载索引，或创建新索引

        Args:
            file_name: 索引文件名（不含路径和扩展名），如 "diary_5adaf..."
            table_type: 表类型（用于恢复），如 "chunks"
            filter_diary_name: 日记本名称（用于过滤恢复）

        Returns:
            索引实例
        """
        idx_path = self.config.store_path / f"index_{file_name}.usearch"

        try:
            if idx_path.exists():
                # 文件存在，加载已有索引
                logging.info(f"[VectorIndex] 📂 Loading existing index: {file_name}")
                idx = VexusIndex.load(
                    self.config.dimension,
                    self.config.capacity,
                    str(idx_path)
                )
            else:
                # ✅ 修改点：文件不存在时，从数据库恢复
                logging.info(f"[VectorIndex] ✨ Creating new index and rebuilding from DB: {file_name}")
                idx = VexusIndex(self.config.dimension, self.config.capacity)

                # 从数据库恢复数据到索引
                if filter_diary_name:
                    await self._recover_from_database(idx, filter_diary_name)
                    logging.info(f"[VectorIndex] ✅ Rebuilt index for \"{filter_diary_name}\" from database")
        
        except Exception as e:
            logging.error(f"[VectorIndex] ❌ Index load error ({file_name}): {e}")
            logging.warning("[VectorIndex] 🔄 Creating new index as fallback...")
            idx = VexusIndex(self.config.dimension, self.config.capacity)

        return idx

    # ==================== 3. 添加向量 ====================
    async def add_vector(self, diary_name: str, id: int, vector_buffer: bytes) -> None:
        """
        向日记本索引添加向量

        Args:
            diary_name: 日记本名称
            id: 向量ID（如chunk_id）
            vector_buffer: 向量数据的bytes
        """
        logging.info(f"[VectorIndex] ➕ Adding vector {id} to diary \"{diary_name}\"")

        # 通过懒加载获取索引
        idx = await self._get_or_load_diary_index(diary_name)

        # 添加向量到索引
        try:
            idx.add(id, vector_buffer)
        except Exception as e:
            error_msg = str(e)
            if "Duplicate" in error_msg:
                # 处理重复ID：先删除再添加（upsert）
                logging.warning(f"[VectorIndex] ⚠️ Duplicate ID {id}, performing upsert...")
                if hasattr(idx, "remove"):
                    idx.remove(id)
                idx.add(id, vector_buffer)
            else:
                raise

        # 安排延迟保存
        self._schedule_index_save(diary_name)

    async def add_vectors(self, diary_name: str, vectors: List[Tuple[int, bytes]]) -> None:
        """
        批量添加向量

        Args:
            diary_name: 日记本名称
            vectors: 向量数组，每个元素为 (id, vec) 元组
        """
        logging.info(f"[VectorIndex] ➕➕ Adding {len(vectors)} vectors to diary \"{diary_name}\"")

        idx = await self._get_or_load_diary_index(diary_name)

        for id, vec in vectors:
            try:
                idx.add(id, vec)
            except Exception as e:
                error_msg = str(e)
                if "Duplicate" in error_msg:
                    if hasattr(idx, "remove"):
                        idx.remove(id)
                    idx.add(id, vec)

        self._schedule_index_save(diary_name)

    # ==================== 4. 保存到磁盘 ====================
    def _schedule_index_save(self, diary_name: str) -> None:
        """
        安排延迟保存（防抖）

        Args:
            diary_name: 日记本名称
        """
        # 如果已有任务，取消它
        if diary_name in self.save_tasks and self.save_tasks[diary_name] is not None:
            self.save_tasks[diary_name].cancel()

        # 创建新的延迟保存任务
        async def save_task():
            await asyncio.sleep(self.config.index_save_delay)
            await self._save_index_to_disk(diary_name)
            self.save_tasks[diary_name] = None

        task = asyncio.create_task(save_task())
        self.save_tasks[diary_name] = task
        logging.info(
            f"[VectorIndex] ⏰ Scheduled save for \"{diary_name}\" "
            f"in {self.config.index_save_delay}s"
        )

    async def _save_index_to_disk(self, diary_name: str) -> None:
        """
        立即保存索引到磁盘

        Args:
            diary_name: 日记本名称
        """
        try:
            # 获取日记本的MD5哈希
            safe_name = hashlib.md5(diary_name.encode()).hexdigest()

            # 获取索引实例
            idx = self.diary_indices.get(diary_name)
            if idx is None:
                logging.warning(f"[VectorIndex] ⚠️ No index found for \"{diary_name}\", skipping save.")
                return

            # 构建文件路径
            file_path = self.config.store_path / f"index_diary_{safe_name}.usearch"

            # 保存到磁盘
            idx.save(str(file_path))
            logging.info(f"[VectorIndex] 💾 Saved index: \"{diary_name}\" -> index_diary_{safe_name}.usearch")
        except Exception as e:
            logging.error(f"[VectorIndex] ❌ Save failed for \"{diary_name}\": {e}")


    async def process_diary_file(
        self,
        character_id: str,
        file_path: str
    ) -> Dict[str, Any]:
        """
        完整流程：处理单个日记文件

        流程：
        1. 读取文件内容，计算校验和
        2. 检查数据库是否已存在（通过校验和判断是否需要更新）
        3. 文本分块
        4. 向量化
        5. 存入数据库
        6. 创建/更新向量索引

        Args:
            character_id: 角色ID
            file_path: 日记文件路径（相对于 data/characters/{character_id}/daily/）

        Returns:
            处理结果：{file_id, chunk_count, updated, diary_name, skipped}
        """
        diary_dir = self._get_diary_dir(character_id)
        full_path = diary_dir / file_path

        # 检查文件是否存在
        if not full_path.exists():
            logging.warning(f"[VectorIndex] File not found: {full_path}")
            return {"error": "file_not_found", "path": str(full_path)}

        # 获取角色名称（用于diary_name）
        character_service = CharacterService()
        character = character_service.get_character(character_id)
        if not character:
            logging.error(f"[VectorIndex] Character not found: {character_id}")
            return {"error": "character_not_found", "character_id": character_id}
        diary_name = character.name

        try:
            # 1. 读取文件内容
            content = full_path.read_text(encoding='utf-8')

            # 2. 计算文件元数据
            checksum = self._calculate_checksum(content)
            mtime = int(full_path.stat().st_mtime)
            size = len(content.encode('utf-8'))
            updated_at = int(time.time())

            # 3. 检查数据库是否已存在且无需更新
            db: Session = SessionLocal()
            try:
                existing_file = db.query(DiaryFileTable).filter(
                    DiaryFileTable.path == file_path
                ).first()

                if existing_file and existing_file.checksum == checksum:
                    logging.info(f"[VectorIndex] File unchanged, skipping: {file_path}")
                    return {
                        "file_id": existing_file.id,
                        "chunk_count": len(existing_file.chunks),
                        "updated": False,
                        "diary_name": diary_name,
                        "skipped": True
                    }

                # 4. 文本分块
                chunks = chunk_text(content)
                if not chunks:
                    logging.warning(f"[VectorIndex] No chunks generated for: {file_path}")
                    return {"error": "no_chunks", "path": str(full_path)}

                # 5. 向量化
                vectors = await self._vectorize_chunks(chunks)
                if not vectors or all(v is None for v in vectors):
                    logging.error(f"[VectorIndex] All vectorizations failed for: {file_path}")
                    return {"error": "vectorization_failed", "path": str(full_path)}

                # 6. 更新或插入数据库
                if existing_file:
                    # 删除旧的chunks
                    db.query(ChunkTable).filter(ChunkTable.file_id == existing_file.id).delete()
                    # 更新文件记录
                    existing_file.checksum = checksum
                    existing_file.mtime = mtime
                    existing_file.size = size
                    existing_file.updated_at = updated_at
                    file_id = existing_file.id
                    db.flush()
                    logging.info(f"[VectorIndex] Updating existing file: {file_path}")
                else:
                    # 创建新文件记录
                    new_file = DiaryFileTable(
                        path=file_path,
                        diary_name=diary_name,
                        checksum=checksum,
                        mtime=mtime,
                        size=size,
                        updated_at=updated_at
                    )
                    db.add(new_file)
                    db.flush()
                    file_id = new_file.id
                    logging.info(f"[VectorIndex] Creating new file record: {file_path}")

                # 7. 插入chunks
                chunk_entries = []
                vector_tuples = []
                valid_chunk_count = 0

                for i, (text, vector) in enumerate(zip(chunks, vectors)):
                    if vector is None:
                        logging.warning(f"[VectorIndex] Vectorization failed for chunk {i}")
                        continue

                    # 存储向量到数据库（JSON格式）
                    chunk_entry = ChunkTable(
                        file_id=file_id,
                        chunk_index=i,
                        content=text,
                        vector=json.dumps(vector)
                    )
                    chunk_entries.append(chunk_entry)

                    # 准备向量索引数据
                    vector_bytes = self._serialize_vector(vector)
                    vector_tuples.append((file_id * 10000 + i, vector_bytes))
                    valid_chunk_count += 1

                db.add_all(chunk_entries)
                db.commit()

                # 8. 创建/更新向量索引
                if vector_tuples:
                    await self.add_vectors(diary_name, vector_tuples)
                    logging.info(
                        f"[VectorIndex] Added {valid_chunk_count} vectors to index for: {file_path}"
                    )

                return {
                    "file_id": file_id,
                    "chunk_count": valid_chunk_count,
                    "updated": True,
                    "diary_name": diary_name,
                    "skipped": False
                }

            except Exception as e:
                db.rollback()
                logging.error(f"[VectorIndex] Database error processing {file_path}: {e}")
                return {"error": "database_error", "detail": str(e)}
            finally:
                db.close()

        except Exception as e:
            logging.error(f"[VectorIndex] Error processing file {file_path}: {e}")
            return {"error": "processing_error", "detail": str(e)}

    async def sync_character_diaries(
        self,
        character_id: str
    ) -> Dict[str, Any]:
        """
        同步指定角色的所有日记文件

        Args:
            character_id: 角色ID

        Returns:
            同步结果：{processed, skipped, failed, total_chunks, files}
        """
        diary_dir = self._get_diary_dir(character_id)

        if not diary_dir.exists():
            logging.warning(f"[VectorIndex] Diary directory not found: {diary_dir}")
            return {
                "processed": 0,
                "skipped": 0,
                "failed": 0,
                "total_chunks": 0,
                "files": []
            }

        # 获取所有.txt文件
        txt_files = sorted(diary_dir.glob("*.txt"))
        logging.info(f"[VectorIndex] Found {len(txt_files)} diary files for {character_id}")

        results = {
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "total_chunks": 0,
            "files": []
        }

        # 处理每个文件
        for file_path in txt_files:
            relative_path = file_path.name  # 只保留文件名
            result = await self.process_diary_file(character_id, relative_path)

            file_result = {
                "path": relative_path,
                "status": "unknown"
            }

            if "error" in result:
                results["failed"] += 1
                file_result["status"] = "failed"
                file_result["error"] = result["error"]
            elif result.get("skipped"):
                results["skipped"] += 1
                file_result["status"] = "skipped"
            else:
                results["processed"] += 1
                results["total_chunks"] += result.get("chunk_count", 0)
                file_result["status"] = "processed"
                file_result["chunk_count"] = result.get("chunk_count", 0)

            results["files"].append(file_result)

        logging.info(
            f"[VectorIndex] Sync complete for {character_id}: "
            f"{results['processed']} processed, {results['skipped']} skipped, "
            f"{results['failed']} failed, {results['total_chunks']} total chunks"
        )

        return results

    async def rebuild_index_from_db(
        self,
        diary_name: str
    ) -> None:
        """
        从数据库重建向量索引

        Args:
            diary_name: 日记本名称（角色名称）
        """
        logging.info(f"[VectorIndex] Rebuilding index for diary: {diary_name}")

        db: Session = SessionLocal()
        try:
            # 查询所有chunks
            chunks = db.query(ChunkTable).join(DiaryFileTable).filter(
                DiaryFileTable.diary_name == diary_name
            ).order_by(ChunkTable.chunk_index).all()

            if not chunks:
                logging.warning(f"[VectorIndex] No chunks found for diary: {diary_name}")
                return

            # 准备向量数据
            vector_tuples = []
            for chunk in chunks:
                try:
                    vector = json.loads(chunk.vector)
                    vector_bytes = self._serialize_vector(vector)
                    # 使用 chunk.id 作为向量ID
                    vector_tuples.append((chunk.id, vector_bytes))
                except (json.JSONDecodeError, TypeError) as e:
                    logging.warning(f"[VectorIndex] Failed to parse vector for chunk {chunk.id}: {e}")

            if vector_tuples:
                # 获取或加载索引
                idx = await self._get_or_load_diary_index(diary_name)

                # 清空现有索引（如果需要完全重建）
                # 这里我们选择追加模式，如果需要重建可以先删除索引文件

                # 批量添加向量
                await self.add_vectors(diary_name, vector_tuples)
                logging.info(f"[VectorIndex] Rebuilt index with {len(vector_tuples)} vectors")

        finally:
            db.close()

    # ==================== 辅助方法 ====================

    def _serialize_vector(self, vector: List[float]) -> bytes:
        """
        将向量列表序列化为 bytes 格式

        Args:
            vector: 向量列表

        Returns:
            序列化后的bytes
        """
        return struct.pack(f'{len(vector)}f', *vector)

    async def _vectorize_chunks(
        self,
        chunks: List[str]
    ) -> List[Optional[List[float]]]:
        """
        批量向量化文本块

        Args:
            chunks: 文本块列表

        Returns:
            向量列表（失败的项为None）
        """
        if not chunks:
            return []

        try:
            async with EmbeddingService() as embedding_service:
                vectors = await embedding_service.get_embeddings_batch(chunks)
                return vectors
        except Exception as e:
            logging.error(f"[VectorIndex] Vectorization failed: {e}")
            return [None] * len(chunks)

    def _get_diary_dir(self, character_id: str) -> Path:
        """
        获取角色日记目录路径

        Args:
            character_id: 角色ID

        Returns:
            日记目录路径
        """
        # CharacterService uses a different base path
        # We need to match it
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
        return project_root / "data" / "characters" / character_id / "daily"

    def _calculate_checksum(self, content: str) -> str:
        """
        计算文本内容的MD5校验和

        Args:
            content: 文本内容

        Returns:
            MD5哈希字符串
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    # ==================== 原有辅助方法 ====================

    def stats(self) -> Dict[str, Dict[str, int]]:
        """
        获取所有已加载索引的统计信息

        Returns:
            字典，key为日记本名称，value为统计信息字典
        """
        result = {}
        for diary_name, idx in self.diary_indices.items():
            stats_obj = idx.stats()
            result[diary_name] = {
                "totalVectors": stats_obj.total_vectors,
                "dimensions": stats_obj.dimensions,
                "capacity": stats_obj.capacity,
                "memoryUsage": stats_obj.memory_usage,
            }
        return result

    def get_stats(self, diary_name: str) -> Optional[Dict[str, int]]:
        """
        获取索引统计信息

        Args:
            diary_name: 日记本名称

        Returns:
            统计信息字典，如果索引不存在则返回None
        """
        idx = self.diary_indices.get(diary_name)
        if idx is None:
            return None
        stats_obj = idx.stats()
        return {
            "totalVectors": stats_obj.total_vectors,
            "dimensions": stats_obj.dimensions,
            "capacity": stats_obj.capacity,
            "memoryUsage": stats_obj.memory_usage,
        }

    async def flush_all(self) -> None:
        """立即保存所有待保存的索引"""
        logging.info("[VectorIndex] 💾💾 Flushing all pending saves...")
        for diary_name, task in list(self.save_tasks.items()):
            if task is not None:
                task.cancel()
                del self.save_tasks[diary_name]
                await self._save_index_to_disk(diary_name)
        logging.info("[VectorIndex] ✅ All indices saved.")

    def get_index_path(self, diary_name: str) -> Path:
        """
        获取索引文件路径（供调试用）

        Args:
            diary_name: 日记本名称

        Returns:
            索引文件路径
        """
        safe_name = hashlib.md5(diary_name.encode()).hexdigest()
        return self.config.store_path / f"index_diary_{safe_name}.usearch"


    async def _recover_from_database(
        self,
        idx: VexusIndex,
        diary_name: str
    ) -> None:
        """
        从数据库恢复向量数据到索引

        Args:
            idx: 索引实例
            diary_name: 日记本名称
        """
        db: Session = SessionLocal()
        try:
            # 查询该日记本的所有 chunks
            chunks = db.query(ChunkTable).join(DiaryFileTable).filter(
                DiaryFileTable.diary_name == diary_name
            ).order_by(ChunkTable.id).all()

            if not chunks:
                logging.warning(f"[VectorIndex] No chunks found in DB for diary: {diary_name}")
                return

            # 批量添加向量到索引
            added_count = 0
            for chunk in chunks:
                if not chunk.vector:
                    continue

                try:
                    vector = json.loads(chunk.vector)
                    vector_bytes = self._serialize_vector(vector)
                    idx.add(chunk.id, vector_bytes)
                    added_count += 1
                except (json.JSONDecodeError, TypeError) as e:
                    logging.warning(f"[VectorIndex] Failed to parse vector for chunk {chunk.id}: {e}")

            logging.info(f"[VectorIndex] ✅ Recovered {added_count} vectors from database")

        finally:
            db.close()