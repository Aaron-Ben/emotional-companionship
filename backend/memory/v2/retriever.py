"""
Hierarchical retriever for V2 memory system.

基于 ChromaDB 多层级向量检索 + 分数传播的层级记忆检索实现。
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

logger = logging.getLogger(__name__)

# 数据目录基础路径
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"

# Score propagation: weight for direct vector score vs sibling boost
SCORE_PROPAGATION_ALPHA = 0.7


class ContextType(str, Enum):
    """Context type for retrieval."""
    MEMORY = "memory"
    SESSION = "session"


class SpaceType(str, Enum):
    """Space type for retrieval."""
    USER = "user"
    AGENT = "agent"


@dataclass
class RelatedContext:
    """Related context with summary."""
    uri: str
    abstract: str


@dataclass
class MatchedContext:
    """Matched context from retrieval."""
    uri: str
    context_type: ContextType
    level: int = 2
    abstract: str = ""
    overview: Optional[str] = None
    category: str = ""
    score: float = 0.0
    match_reason: str = ""
    relations: List[RelatedContext] = field(default_factory=list)


@dataclass
class QueryResult:
    """Result for a query."""
    query: str
    matched_contexts: List[MatchedContext]
    searched_directories: List[str]


class HierarchicalRetriever:
    """层级记忆检索器，支持多层级 ChromaDB 搜索和分数传播。"""

    def __init__(
        self,
        chromadb_manager: Any,
        embedding_service: Any,
        data_dir: Optional[Path] = None,
    ):
        self._chromadb = chromadb_manager
        self._embedding = embedding_service
        self._data_dir = data_dir or DATA_DIR

    async def retrieve(
        self,
        query: str,
        user: str,
        space: SpaceType = SpaceType.USER,
        limit: int = 5,
    ) -> QueryResult:
        """检索记忆.

        Args:
            query: 查询文本
            user: 用户/代理标识
            space: 空间类型 (USER 或 AGENT)
            limit: 返回结果数量限制

        Returns:
            QueryResult: 包含 matched_contexts 和 searched_directories
        """
        # Step 1: 向量化查询
        query_vector = await self._embedding.get_single_embedding(query)
        if not query_vector:
            logger.warning("[HierarchicalRetriever] Failed to embed query")
            return QueryResult(
                query=query,
                matched_contexts=[],
                searched_directories=[],
            )

        results: List[MatchedContext] = []

        # Step 2: ChromaDB 向量检索 (all levels: L0, L1, L2)
        chroma_results = await self._search_all_levels(
            query_vector=query_vector,
            user=user,
            space=space,
            limit=limit,
        )
        results.extend(chroma_results)

        # Step 3: 分数传播
        results = self._propagate_scores(results)

        # Step 4: 会话文件检索 (filesystem, sessions not in ChromaDB)
        session_results = await self._search_session_files(user, limit)
        results.extend(session_results)

        # Step 5: 按 score 排序并返回
        results.sort(key=lambda x: x.score, reverse=True)
        final_results = results[:limit]

        logger.info(
            f"[HierarchicalRetriever] Retrieved {len(final_results)} results "
            f"for query: {query[:50]}..."
        )

        return QueryResult(
            query=query,
            matched_contexts=final_results,
            searched_directories=self._get_search_directories(user, space),
        )

    async def _search_all_levels(
        self,
        query_vector: List[float],
        user: str,
        space: SpaceType,
        limit: int,
    ) -> List[MatchedContext]:
        """从 ChromaDB 检索全部层级 (L0, L1, L2) 的向量匹配结果."""
        if space == SpaceType.AGENT:
            owner_space = f"agent:{user}"
        else:
            owner_space = user

        category_prefix = f"data/{space.value}/{user}/memories/"

        try:
            # Search all levels — limit*3 to account for multi-level records per URI
            chroma_results = await self._chromadb.search_similar_memories(
                owner_space=owner_space,
                category_uri_prefix=category_prefix,
                query_vector=query_vector,
                limit=limit,
                # No level_filter → search L0, L1, L2
            )

            # De-duplicate by URI: keep the highest-scoring record per URI
            best_by_uri: Dict[str, MatchedContext] = {}
            for r in chroma_results:
                uri = r.get("uri", "")
                score = r.get("_score", 0.0)
                if uri not in best_by_uri or score > best_by_uri[uri].score:
                    best_by_uri[uri] = MatchedContext(
                        uri=uri,
                        context_type=ContextType.MEMORY,
                        level=r.get("level", 2),
                        abstract=r.get("abstract", ""),
                        overview=r.get("overview", None),
                        category=r.get("category", ""),
                        score=score,
                    )

            return list(best_by_uri.values())

        except Exception as e:
            logger.error(f"[HierarchicalRetriever] ChromaDB search failed: {e}")
            return []

    def _propagate_scores(self, results: List[MatchedContext]) -> List[MatchedContext]:
        """基于 parent_uri 的分数传播：同一目录下的兄弟记忆互相提升分数.

        公式: final_score = alpha * self_score + (1 - alpha) * max(sibling_scores)
        单条记忆（无兄弟）保持原分不变。
        """
        if not results:
            return results

        # Group by parent directory (derived from URI)
        parent_groups: Dict[str, List[MatchedContext]] = {}
        for r in results:
            # e.g. "data/user/u1/memories/preferences/mem_xxx.md" → "data/user/u1/memories/preferences"
            parent_key = r.uri.rsplit("/", 1)[0] if "/" in r.uri else r.uri
            parent_groups.setdefault(parent_key, []).append(r)

        propagated = []
        for ctx in results:
            parent_key = ctx.uri.rsplit("/", 1)[0] if "/" in ctx.uri else ctx.uri
            siblings = parent_groups.get(parent_key, [])

            if len(siblings) <= 1:
                # No siblings, keep original score
                propagated.append(ctx)
                continue

            # Max sibling score (excluding self)
            sibling_scores = [s.score for s in siblings if s.uri != ctx.uri]
            max_sibling_score = max(sibling_scores) if sibling_scores else 0.0

            # Weighted combination
            final_score = (
                SCORE_PROPAGATION_ALPHA * ctx.score
                + (1 - SCORE_PROPAGATION_ALPHA) * max_sibling_score
            )
            ctx.score = final_score
            propagated.append(ctx)

        return propagated

    async def _search_session_files(
        self,
        user: str,
        limit: int,
    ) -> List[MatchedContext]:
        """搜索会话目录中的 .abstract.md 和 .overview.md 文件.

        会话文件不进入 ChromaDB，使用简单的关键词匹配。
        """
        results: List[MatchedContext] = []
        session_dir = self._data_dir / "session" / user

        if not session_dir.exists():
            return results

        try:
            for session_path in session_dir.iterdir():
                if not session_path.is_dir():
                    continue

                session_id = session_path.name

                # 读取 .abstract.md (L0)
                abstract_file = session_path / ".abstract.md"
                if abstract_file.exists():
                    content = await self._read_file(abstract_file)
                    if content:
                        results.append(
                            MatchedContext(
                                uri=f"session/{session_id}/.abstract.md",
                                context_type=ContextType.SESSION,
                                level=0,
                                abstract=content,
                                category="session",
                                score=0.1,  # baseline score for session files
                            )
                        )

                # 读取 .overview.md (L1)
                overview_file = session_path / ".overview.md"
                if overview_file.exists():
                    content = await self._read_file(overview_file)
                    if content:
                        results.append(
                            MatchedContext(
                                uri=f"session/{session_id}/.overview.md",
                                context_type=ContextType.SESSION,
                                level=1,
                                overview=content,
                                category="session",
                                score=0.1,
                            )
                        )

                # 读取历史归档
                history_dir = session_path / "history"
                if history_dir.exists():
                    for archive_dir in history_dir.iterdir():
                        if not archive_dir.is_dir():
                            continue

                        archive_abstract = archive_dir / ".abstract.md"
                        if archive_abstract.exists():
                            content = await self._read_file(archive_abstract)
                            if content:
                                results.append(
                                    MatchedContext(
                                        uri=f"session/{session_id}/history/{archive_dir.name}/.abstract.md",
                                        context_type=ContextType.SESSION,
                                        level=0,
                                        abstract=content,
                                        category="session_archive",
                                        score=0.1,
                                    )
                                )

                        archive_overview = archive_dir / ".overview.md"
                        if archive_overview.exists():
                            content = await self._read_file(archive_overview)
                            if content:
                                results.append(
                                    MatchedContext(
                                        uri=f"session/{session_id}/history/{archive_dir.name}/.overview.md",
                                        context_type=ContextType.SESSION,
                                        level=1,
                                        overview=content,
                                        category="session_archive",
                                        score=0.1,
                                    )
                                )
        except Exception as e:
            logger.error(f"[HierarchicalRetriever] Failed to search session files: {e}")

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    async def _read_file(self, file_path: Path) -> str:
        """异步读取文件内容."""
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                return await f.read()
        except Exception as e:
            logger.warning(f"[HierarchicalRetriever] Failed to read {file_path}: {e}")
            return ""

    def _get_search_directories(self, user: str, space: SpaceType) -> List[str]:
        """获取检索的目录列表."""
        return [
            f"data/{space.value}/{user}/memories",
            f"data/session/{user}",
        ]


__all__ = [
    "HierarchicalRetriever",
    "MatchedContext",
    "RelatedContext",
    "QueryResult",
    "ContextType",
    "SpaceType",
]
