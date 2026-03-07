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
        name: str,
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
            name: 角色名称
            file_path: 日记文件路径（相对于 data/characters/{name}/daily/）

        Returns:
            处理结果：{file_id, chunk_count, updated, diary_name, skipped}
        """
        diary_dir = self._get_diary_dir(name)
        full_path = diary_dir / file_path

        logging.info(f"[VectorIndex] 📄 开始处理文件: {file_path}")

        # 检查文件是否存在
        if not full_path.exists():
            logging.warning(f"[VectorIndex] ❌ 文件不存在: {full_path}")
            return {"error": "file_not_found", "path": str(full_path)}

        # 获取角色名称（用于diary_name）
        character_service = CharacterService()
        character = character_service.get_character_by_name(name)
        if not character:
            logging.error(f"[VectorIndex] ❌ 角色不存在: {name}")
            return {"error": "character_not_found", "name": name}
        diary_name = character.name

        try:
            # 1. 读取文件内容
            logging.debug(f"[VectorIndex] 📖 读取文件内容...")
            content = full_path.read_text(encoding='utf-8')
            content_length = len(content)
            logging.debug(f"[VectorIndex] ✅ 文件内容读取成功 ({content_length} 字符)")

            # 2. 计算文件元数据
            checksum = self._calculate_checksum(content)
            mtime = int(full_path.stat().st_mtime)
            size = len(content.encode('utf-8'))
            updated_at = int(time.time())
            logging.debug(f"[VectorIndex] 🔍 校验和: {checksum}, 大小: {size} bytes")

            # 3. 检查数据库是否已存在且无需更新
            db: Session = SessionLocal()
            try:
                existing_file = db.query(DiaryFileTable).filter(
                    DiaryFileTable.path == file_path
                ).first()

                if existing_file and existing_file.checksum == checksum:
                    existing_chunks = len(existing_file.chunks)
                    logging.info(f"[VectorIndex] ⏭️  文件未变化，跳过处理: {file_path} (已有 {existing_chunks} 个分块)")
                    return {
                        "file_id": existing_file.id,
                        "chunk_count": existing_chunks,
                        "updated": False,
                        "diary_name": diary_name,
                        "skipped": True
                    }

                # 4. 文本分块
                logging.debug(f"[VectorIndex] ✂️  开始文本分块...")
                chunks = chunk_text(content)
                if not chunks:
                    logging.warning(f"[VectorIndex] ⚠️  无法生成文本分块: {file_path}")
                    return {"error": "no_chunks", "path": str(full_path)}
                logging.debug(f"[VectorIndex] ✅ 生成了 {len(chunks)} 个文本分块")

                # 5. 向量化
                logging.debug(f"[VectorIndex] 🔄 开始向量化...")
                vectors = await self._vectorize_chunks(chunks)
                if not vectors or all(v is None for v in vectors):
                    logging.error(f"[VectorIndex] ❌ 向量化全部失败: {file_path}")
                    return {"error": "vectorization_failed", "path": str(full_path)}
                success_count = sum(1 for v in vectors if v is not None)
                logging.debug(f"[VectorIndex] ✅ 向量化完成: {success_count}/{len(chunks)} 成功")

                # 6. 更新或插入数据库
                if existing_file:
                    # 删除旧的chunks
                    logging.debug(f"[VectorIndex] 🗑️  删除旧的分块数据...")
                    db.query(ChunkTable).filter(ChunkTable.file_id == existing_file.id).delete()
                    # 更新文件记录
                    existing_file.checksum = checksum
                    existing_file.mtime = mtime
                    existing_file.size = size
                    existing_file.updated_at = updated_at
                    file_id = existing_file.id
                    db.flush()
                    logging.info(f"[VectorIndex] 🔄 更新现有文件记录: {file_path}")
                else:
                    # 创建新文件记录
                    logging.debug(f"[VectorIndex] ➕ 创建新文件记录...")
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
                    logging.info(f"[VectorIndex] ✨ 创建新文件记录: {file_path}")

                # 7. 插入chunks
                logging.debug(f"[VectorIndex] 💾 插入分块到数据库...")
                chunk_entries = []
                vector_tuples = []
                valid_chunk_count = 0

                for i, (text, vector) in enumerate(zip(chunks, vectors)):
                    if vector is None:
                        logging.warning(f"[VectorIndex] ⚠️  分块 {i} 向量化失败，跳过")
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
                logging.debug(f"[VectorIndex] ✅ 已插入 {valid_chunk_count} 个分块到数据库")

                # 8. 创建/更新向量索引
                if vector_tuples:
                    logging.debug(f"[VectorIndex] 📊 添加向量到索引...")
                    await self.add_vectors(diary_name, vector_tuples)
                    logging.info(
                        f"[VectorIndex] ✅ 已添加 {valid_chunk_count} 个向量到索引: {file_path}"
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
        name: str
    ) -> Dict[str, Any]:
        """
        同步指定角色的所有日记文件

        Args:
            name: 日记名称

        Returns:
            同步结果：{processed, skipped, failed, total_chunks, files}
        """
        diary_dir = self._get_diary_dir(name)

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
        logging.info(f"[VectorIndex] Found {len(txt_files)} diary files for {name}")

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
            result = await self.process_diary_file(name, relative_path)

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
            f"[VectorIndex] Sync complete for {name}: "
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
                # 批量添加向量（会自动触发索引加载）
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

    def _get_diary_dir(self, name: str) -> Path:
        """
        获取角色日记目录路径

        Args:
            name: 角色名称

        Returns:
            日记目录路径 (data/daily/{sanitized_name}/)
        """
        # Sanitize name the same way CharacterService does
        import re
        sanitized = re.sub(r'[\\/:*?"<>|]', '', name.strip())
        sanitized = re.sub(r'\s+', '_', sanitized)
        sanitized = sanitized[:100] if len(sanitized) > 100 else sanitized
        sanitized = sanitized or 'unnamed'

        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
        return project_root / "data" / "daily" / sanitized

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


# ==================== 统一同步服务 ====================

async def sync_all_diaries_to_vector_index() -> Dict[str, int]:
    """
    统一的同步服务函数：同步所有角色的日记到向量索引

    可在以下场景调用：
    - 应用启动时
    - 创建日记后
    - 更新日记后

    Returns:
        统计信息字典：{processed, skipped, failed, total_chunks}
    """
    from app.services.character_service import CharacterService

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("🚀 启动向量索引同步任务")
    logger.info("=" * 60)

    try:
        # 初始化向量索引
        config = VectorIndexConfig()
        vector_index = VectorIndex(config)
        logger.info("✅ VectorIndex 初始化成功")

        # 获取所有角色
        character_service = CharacterService()
        characters = character_service.list_characters()

        if not characters:
            logger.info("📭 没有找到任何角色")
            return {"processed": 0, "skipped": 0, "failed": 0, "total_chunks": 0}

        logger.info(f"📚 找到 {len(characters)} 个角色，开始同步日记...")

        # 统计信息
        total_stats = {
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "total_chunks": 0
        }

        # 逐个同步角色的日记
        for character in characters:
            logger.info("-" * 60)
            logger.info(f"📖 正在处理角色: {character.name} (ID: {character.character_id})")

            result = await vector_index.sync_character_diaries(character.name)

            # 记录详细结果
            processed = result.get("processed", 0)
            skipped = result.get("skipped", 0)
            failed = result.get("failed", 0)
            total_chunks = result.get("total_chunks", 0)
            files = result.get("files", [])

            logger.info(f"  ✅ 处理: {processed} 个文件")
            logger.info(f"  ⏭️  跳过: {skipped} 个文件")
            logger.info(f"  ❌ 失败: {failed} 个文件")
            logger.info(f"  📦 总分块: {total_chunks} 个")

            # 记录每个文件的处理详情
            if files:
                logger.info("  📄 文件详情:")
                for file_info in files:
                    path = file_info.get("path", "unknown")
                    status = file_info.get("status", "unknown")

                    if status == "processed":
                        chunks = file_info.get("chunk_count", 0)
                        logger.info(f"    ✅ {path}: 已处理 ({chunks} 个分块)")
                    elif status == "skipped":
                        logger.info(f"    ⏭️  {path}: 已跳过 (内容未变化)")
                    elif status == "failed":
                        error = file_info.get("error", "unknown")
                        logger.warning(f"    ❌ {path}: 处理失败 - {error}")

            # 累计统计
            total_stats["processed"] += processed
            total_stats["skipped"] += skipped
            total_stats["failed"] += failed
            total_stats["total_chunks"] += total_chunks

        # 保存所有索引到磁盘
        logger.info("-" * 60)
        await vector_index.flush_all()
        logger.info("💾 所有索引已保存到磁盘")

        # 输出总体统计
        logger.info("=" * 60)
        logger.info("📊 向量索引同步完成 - 总体统计")
        logger.info("=" * 60)
        logger.info(f"  处理文件: {total_stats['processed']}")
        logger.info(f"  跳过文件: {total_stats['skipped']}")
        logger.info(f"  失败文件: {total_stats['failed']}")
        logger.info(f"  总分块数: {total_stats['total_chunks']}")
        logger.info("=" * 60)

        # 显示索引统计
        stats = vector_index.stats()
        if stats:
            logger.info("📈 索引统计详情:")
            for diary_name, stat in stats.items():
                logger.info(f"  📖 {diary_name}:")
                logger.info(f"    向量数: {stat['totalVectors']}")
                logger.info(f"    维度: {stat['dimensions']}")
                logger.info(f"    容量: {stat['capacity']}")
                logger.info(f"    内存使用: {stat['memoryUsage']} bytes")

        return total_stats

    except Exception as e:
        logger.error(f"❌ 向量索引同步失败: {e}", exc_info=True)
        logger.error("请检查向量索引配置和数据库连接")
        return {"processed": 0, "skipped": 0, "failed": 0, "total_chunks": 0}