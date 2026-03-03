"""
RAGDailyPlugin - 日记检索插件

根据时间表达式从日记中检索相关内容，作为用户主入口文件。
用户可根据需要扩展此文件。

Features:
- 时间表达式解析
- 上下文向量管理
- 嵌入投影分析 (EPA)
- 残差金字塔分析
- 智能结果去重
"""

import json
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

from .time_parser import TimeExpressionParser, TimeRange
from .context_vector_manager import ContextVectorManager
from .epa_module import EPAModule
from .residual_pyramid import ResidualPyramid
from .result_deduplicator import ResultDeduplicator

from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)


class RAGDailyPlugin:
    """日记检索插件主类"""

    def __init__(self):
        self.time_parser = TimeExpressionParser()
        self.context_manager: Optional[ContextVectorManager] = None
        self.epa_module: Optional[EPAModule] = None
        self.residual_pyramid: Optional[ResidualPyramid] = None
        self.deduplicator: Optional[ResultDeduplicator] = None
        self.embedding_service: Optional[EmbeddingService] = None

        # Database access
        self.db_session_factory = None
        self.vector_db_manager = None

        self.config: Dict[str, Any] = {}
        self.dependencies: Dict[str, Any] = {}
        self.initialized = False

        # Vector dimension (bge-m3 default)
        self.vector_dimension = 1024

    async def initialize(self, config: Dict[str, Any], dependencies: Dict[str, Any]) -> None:
        """
        初始化插件

        Args:
            config: 插件配置
            dependencies: 依赖注入 (如 vectorDBManager, db_session)
        """
        self.config = config
        self.dependencies = dependencies

        # Extract dependencies
        self.vector_db_manager = dependencies.get("vectorDBManager")
        self.db_session_factory = dependencies.get("db_session")

        # Initialize embedding service
        self.embedding_service = EmbeddingService()

        # Initialize components
        self.context_manager = ContextVectorManager(
            decay_rate=config.get("context_decay_rate", 0.75),
            max_context_window=config.get("max_context_window", 10),
        )
        self.epa_module = EPAModule(
            max_basis_dim=config.get("epa_max_basis_dim", 64),
            cluster_count=config.get("epa_cluster_count", 32),
        )
        self.residual_pyramid = ResidualPyramid(
            max_levels=config.get("pyramid_max_levels", 3),
            top_k=config.get("pyramid_top_k", 10),
        )
        self.deduplicator = ResultDeduplicator(
            max_results=config.get("max_results", 20),
            redundancy_threshold=config.get("redundancy_threshold", 0.85),
        )

        # Initialize EPA module with tags
        await self._initialize_epa()

        self.initialized = True
        logger.info("[RAGDailyPlugin] Initialized successfully")

    async def _initialize_epa(self) -> None:
        """Initialize EPA module with tag vectors from database."""
        if self.db_session_factory is None:
            logger.warning("[RAGDailyPlugin] No database session, skipping EPA initialization")
            return

        try:
            from app.models.database import TagTable
            from sqlalchemy import select

            async with self.db_session_factory() as session:
                result = await session.execute(
                    select(TagTable).where(TagTable.vector.isnot(None)
                ))
                tags = result.scalars().all()

            # Extract vectors
            tag_vectors = []
            for tag in tags:
                if tag.vector:
                    try:
                        vec = json.loads(tag.vector)
                        if not isinstance(vec, list):
                            logger.warning(f"[RAGDailyPlugin] Tag {tag.name} vector is not a list")
                            continue
                        if len(vec) != self.vector_dimension:
                            logger.warning(f"[RAGDailyPlugin] Tag {tag.name} vector has invalid dimension: {len(vec)}")
                            continue
                        tag_vectors.append(np.array(vec, dtype=np.float32))
                    except json.JSONDecodeError as e:
                        logger.warning(f"[RAGDailyPlugin] Tag {tag.name} has invalid JSON: {e}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"[RAGDailyPlugin] Tag {tag.name} has invalid vector format: {e}")

            if tag_vectors:
                await self.epa_module.initialize(tags_vectors=tag_vectors)
                logger.info(f"[RAGDailyPlugin] EPA initialized with {len(tag_vectors)} tag vectors")
        except Exception as e:
            logger.error(f"[RAGDailyPlugin] EPA initialization failed: {e}")

    async def process_messages(self, messages: List[Dict], config: Dict[str, Any]) -> List[Dict]:
        """
        预处理消息 - 检测时间表达式并检索相关日记

        Args:
            messages: 消息列表
            config: 插件配置

        Returns:
            处理后的消息列表（可能附加检索结果）
        """
        if not self.initialized:
            return messages

        # 获取最后一条用户消息
        user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        if not user_message:
            return messages

        # 解析时间表达式
        time_ranges = self.time_parser.parse(user_message)

        if time_ranges:
            # 检测并激活语义组
            activated_groups = self.group_manager.detect_and_activate_groups(user_message)
            logger.info(f"[RAGDailyPlugin] Found {len(time_ranges)} time range(s), {len(activated_groups)} group(s) activated")

            # 执行核心检索
            results = await self._rag_daily_thought_search(
                query=user_message,
                time_ranges=time_ranges,
                activated_groups=activated_groups,
                messages=messages,
            )

            # 将结果附加到最后一条消息
            if results and messages:
                messages[-1]["rag_results"] = results

        # 更新上下文向量
        await self._update_context_vectors(messages)

        return messages

    async def process_tool_call(self, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理工具调用 - 支持通过工具调用方式检索日记

        Args:
            tool_args: 工具参数，可能包含:
                - time_expression: 时间表达式
                - keyword: 搜索关键词
                - groups: 语义组过滤
                - top_k: 返回结果数量

        Returns:
            检索结果
        """
        if not self.initialized:
            return {
                "status": "error",
                "error": "Plugin not initialized"
            }

        time_expression = tool_args.get("time_expression", "")
        keyword = tool_args.get("keyword", "")
        top_k = tool_args.get("top_k", 10)

        # 解析时间
        time_ranges = self.time_parser.parse(time_expression)

        # 检测语义组
        activated_groups = {}
        if keyword:
            activated_groups = self.group_manager.detect_and_activate_groups(keyword)

        # 执行检索
        results = await self._rag_daily_thought_search(
            query=keyword or time_expression,
            time_ranges=time_ranges if time_ranges else None,
            activated_groups=activated_groups,
            top_k=top_k,
        )

        return {
            "status": "success",
            "results": results,
            "count": len(results),
            "time_ranges": [{"start": tr.start.isoformat(), "end": tr.end.isoformat()} for tr in time_ranges] if time_ranges else [],
            "activated_groups": list(activated_groups.keys())
        }

    async def _rag_daily_thought_search(
        self,
        query: str,
        time_ranges: Optional[List[TimeRange]] = None,
        activated_groups: Optional[Dict[str, Dict]] = None,
        messages: Optional[List[Dict]] = None,
        top_k: int = 20,
    ) -> List[Dict]:
        """
        核心检索方法 - 基于向量语义的高级RAG检索

        检索流程:
        1. 解析时间表达式 → time_ranges
        2. 检测语义组 → activated_groups
        3. 生成增强查询向量 → enhanced_vector
        4. 执行向量检索 → candidates
        5. 残差金字塔分析 → pyramid_features
        6. 结果去重 → final_results

        Args:
            query: 查询文本
            time_ranges: 时间范围列表
            activated_groups: 激活的语义组
            messages: 消息列表（用于上下文增强）
            top_k: 返回结果数量

        Returns:
            检索结果列表
        """
        logger.info(f"[RAGDailyPlugin] Starting search for query: {query[:100]}...")

        # Step 1: Generate enhanced query vector
        query_vector = await self._generate_enhanced_query(
            query,
            activated_groups,
            messages,
        )

        if query_vector is None:
            logger.warning("[RAGDailyPlugin] Failed to generate query vector")
            return []

        # Step 2: Retrieve candidates from database
        candidates = await self._retrieve_candidates(
            query_vector=query_vector,
            time_ranges=time_ranges,
            top_k=top_k * 2,  # Get more candidates for deduplication
        )

        if not candidates:
            logger.info("[RAGDailyPlugin] No candidates found")
            return []

        logger.info(f"[RAGDailyPlugin] Retrieved {len(candidates)} candidates")

        # Step 3: Analyze with residual pyramid
        pyramid_features = self.residual_pyramid.analyze(
            query_vector=np.array(query_vector),
            tags=candidates[:self.residual_pyramid.top_k],
        )

        # Step 4: Deduplicate and rank results
        final_results = await self.deduplicator.deduplicate(
            candidates=candidates,
            query_vector=np.array(query_vector),
            pyramid_features=pyramid_features,
        )

        logger.info(f"[RAGDailyPlugin] Returning {len(final_results[:top_k])} final results")

        return final_results[:top_k]

    async def _generate_enhanced_query(
        self,
        query: str,
        activated_groups: Optional[Dict[str, Dict]] = None,
        messages: Optional[List[Dict]] = None,
    ) -> Optional[np.ndarray]:
        """
        生成增强的查询向量

        Args:
            query: 原始查询文本
            activated_groups: 激活的语义组
            messages: 消息列表（用于上下文增强）

        Returns:
            增强后的查询向量
        """
        # 获取基础查询向量
        query_vector = await self.cached_embedding_service.get_single_embedding(query)

        if query_vector is None:
            return None

        # 应用语义组增强
        if activated_groups:
            enhanced_vector = await self.group_manager.get_enhanced_vector(
                original_query=query,
                activated_groups=activated_groups,
                precomputed_query_vector=query_vector,
            )

            if enhanced_vector:
                query_vector = enhanced_vector

        # 应用上下文增强
        if messages and self.context_manager:
            # 获取上下文聚合向量
            context_vector = self.context_manager.aggregate_context(role="assistant")

            if context_vector is not None:
                # 混合查询向量和上下文向量
                from .math_utils import weighted_average
                query_vector = weighted_average(
                    [np.array(query_vector), context_vector],
                    [0.8, 0.2],  # 80% query, 20% context
                )

        return np.array(query_vector) if not isinstance(query_vector, np.ndarray) else query_vector

    async def _retrieve_candidates(
        self,
        query_vector: np.ndarray,
        time_ranges: Optional[List[TimeRange]] = None,
        top_k: int = 40,
    ) -> List[Dict]:
        """
        从数据库检索候选结果

        Args:
            query_vector: 查询向量
            time_ranges: 时间范围过滤
            top_k: 候选数量

        Returns:
            候选结果列表
        """
        if self.db_session_factory is None:
            logger.warning("[RAGDailyPlugin] No database session available")
            return []

        try:
            from app.models.database import ChunkTable, DiaryFileTable
            from sqlalchemy import select, and_

            async with self.db_session_factory() as session:
                # Build query
                query = select(ChunkTable).join(DiaryFileTable)

                # Apply time filter if specified
                if time_ranges:
                    time_conditions = []
                    for tr in time_ranges:
                        # Convert to timestamps
                        start_ts = int(tr.start.timestamp())
                        end_ts = int(tr.end.timestamp())
                        time_conditions.append(
                            and_(
                                DiaryFileTable.mtime >= start_ts,
                                DiaryFileTable.mtime <= end_ts
                            )
                        )

                    if time_conditions:
                        from sqlalchemy import or_
                        query = query.where(or_(*time_conditions))

                # Only get chunks with vectors
                query = query.where(ChunkTable.vector.isnot(None))

                # Execute query
                result = await session.execute(query.limit(top_k * 5))  # Get more for filtering
                chunks = result.scalars().all()

            # Calculate similarities and build candidates
            candidates = []
            query_norm = query_vector / np.linalg.norm(query_vector)

            for chunk in chunks:
                if not chunk.vector:
                    continue

                try:
                    import json
                    chunk_vector = np.array(json.loads(chunk.vector))

                    # Calculate cosine similarity
                    chunk_norm = chunk_vector / np.linalg.norm(chunk_vector)
                    similarity = float(np.dot(query_norm, chunk_norm))

                    candidates.append({
                        "id": chunk.id,
                        "content": chunk.content,
                        "vector": chunk_vector,
                        "score": similarity,
                        "file_id": chunk.file_id,
                        "chunk_index": chunk.chunk_index,
                    })
                except Exception as e:
                    logger.warning(f"[RAGDailyPlugin] Failed to process chunk {chunk.id}: {e}")

            # Sort by similarity
            candidates.sort(key=lambda x: x["score"], reverse=True)

            return candidates[:top_k]

        except Exception as e:
            logger.error(f"[RAGDailyPlugin] Failed to retrieve candidates: {e}")
            return []

    async def _update_context_vectors(self, messages: List[Dict]) -> None:
        """
        更新上下文向量管理器

        Args:
            messages: 消息列表
        """
        if not self.context_manager or not messages:
            return

        # 获取需要向量化消息的向量
        message_vectors = {}

        for msg in messages:
            msg_id = msg.get("id") or f"msg_{hash(msg.get('content', ''))}"
            content = msg.get("content", "")

            if content and msg_id not in self.context_manager.message_vectors:
                vector = await self.cached_embedding_service.get_single_embedding(content)

                if vector:
                    message_vectors[msg_id] = np.array(vector)

        # 更新上下文
        if message_vectors:
            self.context_manager.update_context(
                messages=messages,
                message_vectors=message_vectors,
            )

    async def shutdown(self) -> None:
        """关闭插件，清理资源"""
        # 保存语义组状态
        if self.group_manager:
            await self.group_manager.save_groups()

        # 保存EPA状态
        if self.epa_module and self.db_session_factory:
            await self._save_epa_state()

        # 关闭embedding服务
        if self.embedding_service:
            await self.embedding_service.close()

        # 保存缓存统计
        if self.cached_embedding_service:
            stats = self.cached_embedding_service.get_cache_stats()
            logger.info(f"[RAGDailyPlugin] Cache stats: {stats}")

        logger.info("[RAGDailyPlugin] Shutdown complete")

    async def _save_epa_state(self) -> None:
        """保存EPA状态到数据库"""
        try:
            from app.models.database import KVStoreTable
            from sqlalchemy import select
            import time

            # Helper function to set KV store
            async def kv_set(key: str, value: str, vector: Optional[List[float]] = None):
                async with self.db_session_factory() as session:
                    # Check if exists
                    existing = await session.execute(
                        select(KVStoreTable).where(KVStoreTable.key == key)
                    )
                    existing_obj = existing.scalar_one_or_none()

                    vector_json = json.dumps(vector) if vector else None

                    if existing_obj:
                        existing_obj.value = value
                        existing_obj.vector = vector_json
                        existing_obj.updated_at = int(time.time())
                    else:
                        new_entry = KVStoreTable(
                            key=key,
                            value=value,
                            vector=vector_json,
                            updated_at=int(time.time())
                        )
                        session.add(new_entry)

                    await session.commit()

            await self.epa_module.save_to_cache(kv_set)

        except Exception as e:
            logger.error(f"[RAGDailyPlugin] Failed to save EPA state: {e}")


# 插件实例 (由 PluginManager 加载)
_plugin_instance: Optional[RAGDailyPlugin] = None


def initialize(config: Dict[str, Any], dependencies: Dict[str, Any]) -> None:
    """同步初始化入口 (兼容性)"""
    import asyncio
    global _plugin_instance
    _plugin_instance = RAGDailyPlugin()
    # 使用 asyncio.create_task 或同步方式初始化
    # 这里简化处理，实际应根据环境调整


async def initialize_async(config: Dict[str, Any], dependencies: Dict[str, Any]) -> None:
    """异步初始化入口"""
    global _plugin_instance
    _plugin_instance = RAGDailyPlugin()
    await _plugin_instance.initialize(config, dependencies)


async def process_messages(messages: List[Dict], config: Dict[str, Any]) -> List[Dict]:
    """消息预处理器入口"""
    global _plugin_instance
    if _plugin_instance is None:
        # 自动初始化
        _plugin_instance = RAGDailyPlugin()
    return await _plugin_instance.process_messages(messages, config)


async def process_tool_call(tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """工具调用入口"""
    global _plugin_instance
    if _plugin_instance is None:
        return {"status": "error", "error": "Plugin not initialized"}
    return await _plugin_instance.process_tool_call(tool_args)


async def shutdown() -> None:
    """关闭入口"""
    global _plugin_instance
    if _plugin_instance:
        await _plugin_instance.shutdown()


# 默认使用异步初始化
initialize = initialize_async
