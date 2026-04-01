"""
Hierarchical retriever for V2 memory system.

参考 OpenViking 的目录树导航模式，使用 heapq 优先队列驱动递归检索：
1. 全局搜索 L0+L1 定位起始 category 目录
2. heapq 按分数高低探索各 category，搜索子节点（所有 level）
3. L0/L1 → 继续深入 / L2 → 收集为最终结果
4. 收敛检测：top-k 连续不变则提前退出
"""

import heapq
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import aiofiles

logger = logging.getLogger(__name__)

# 数据目录基础路径
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"


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
    """层级记忆检索器，使用 heapq 优先队列驱动的目录树导航。

    检索管线（参考 OpenViking）：
    1. 全局搜索 L0+L1 → 定位有希望的 category 目录
    2. heapq 优先队列 → 按分数高低探索各 category
    3. 递归搜索子节点 → L0/L1 继续深入，L2 收集结果
    4. 收敛检测 → top-k 连续 N 轮不变则提前退出
    """

    # 剪枝阈值
    MIN_SCORE_THRESHOLD: float = 0.2
    SESSION_BASE_SCORE: float = 0.3
    GLOBAL_SEARCH_TOPK: int = 5

    # 分数传播
    SCORE_PROPAGATION_ALPHA: float = 0.5  # 子级自身权重 (1-α = 父级传播权重)

    # 收敛控制
    MAX_CONVERGENCE_ROUNDS: int = 3
    MAX_TRAVERSAL_ROUNDS: int = 10

    # L2 终端层级
    TERMINAL_LEVEL: int = 2

    def __init__(
        self,
        chromadb_manager: Any,
        embedding_service: Any,
        data_dir: Optional[Path] = None,
    ):
        self._chromadb = chromadb_manager
        self._embedding = embedding_service
        self._data_dir = data_dir or DATA_DIR

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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

        # Step 2: 全局搜索 L0+L1，定位起始 category 目录
        global_results = await self._global_search(query_vector, user, space)

        # Step 3: 确定起始点（全局搜索结果 + 根 category 目录）
        starting_points = self._build_starting_points(user, space, global_results)
        logger.info(
            f"[HierarchicalRetriever] Starting points: {len(starting_points)} "
            f"(global hits: {len(global_results)})"
        )

        # Step 4: heapq 递归搜索
        candidates = await self._recursive_search(
            query_vector=query_vector,
            starting_points=starting_points,
            user=user,
            space=space,
            limit=limit,
        )

        # Step 5: 转换为 MatchedContext
        matched = self._convert_to_matched_contexts(candidates)

        # Step 6: 会话文件补充
        session_results = await self._search_session_files(user, limit)
        matched.extend(session_results)

        # 排序返回
        matched.sort(key=lambda x: x.score, reverse=True)

        logger.info(
            f"[HierarchicalRetriever] Retrieved {len(matched[:limit])} results "
            f"for query: {query[:50]}..."
        )

        return QueryResult(
            query=query,
            matched_contexts=matched[:limit],
            searched_directories=self._get_search_directories(user, space),
        )

    # ------------------------------------------------------------------
    # Step 2: 全局搜索 L0+L1
    # ------------------------------------------------------------------

    async def _global_search(
        self,
        query_vector: List[float],
        user: str,
        space: SpaceType,
    ) -> List[Dict[str, Any]]:
        """全局搜索 L0+L1，定位有希望的起始目录/记忆。

        参考 OpenViking search_global_roots_in_tenant: In("level", [0, 1])
        """
        owner_space = user if space == SpaceType.USER else f"agent:{user}"
        category_prefix = f"data/{space.value}/{user}/memories/"

        try:
            # 搜索所有 level 不过滤，但取更多结果
            # 实际只有 L0/L1/L2 三种，这里取足够多来覆盖 L0+L1
            results = await self._chromadb.search_similar_memories(
                owner_space=owner_space,
                category_uri_prefix=category_prefix,
                query_vector=query_vector,
                limit=self.GLOBAL_SEARCH_TOPK * 3,
            )

            # 只保留 L0 和 L1 结果（过滤掉 L2）
            filtered = [
                r for r in results
                if r.get("level", 2) in (0, 1)
                and r.get("_score", 0.0) >= self.MIN_SCORE_THRESHOLD
            ]

            return filtered

        except Exception as e:
            logger.error(f"[HierarchicalRetriever] Global search failed: {e}")
            return []

    # ------------------------------------------------------------------
    # Step 3: 构建起始点
    # ------------------------------------------------------------------

    def _build_starting_points(
        self,
        user: str,
        space: SpaceType,
        global_results: List[Dict[str, Any]],
    ) -> List[Tuple[str, float]]:
        """合并全局搜索结果与根 category 目录作为起始点。

        Returns:
            List of (uri, score) tuples，uri 可以是 category 目录或具体记忆 uri
        """
        points: List[Tuple[str, float]] = []
        seen: Set[str] = set()

        # 全局搜索命中：提取 category 目录作为起始点
        for r in global_results:
            uri = r.get("uri", "")
            score = r.get("_score", 0.0)
            # 从记忆 uri 提取 category 目录路径
            # e.g. "data/user/test_user/memories/preferences/mem_xxx.md"
            #   → "data/user/test_user/memories/preferences"
            category_dir = self._extract_category_dir(uri)
            if category_dir and category_dir not in seen:
                # 同一 category 可能有多条命中，取最高分
                heapq.heappush(points, (-score, category_dir))
                seen.add(category_dir)

        # 补入所有 category 根目录（未被子覆盖的）
        root_categories = self._get_category_roots(user, space)
        for cat_dir in root_categories:
            if cat_dir not in seen:
                points.append((0.0, cat_dir))  # score=0，最低优先级
                seen.add(cat_dir)

        # 将 heapq 转为按分数降序的列表
        # points 中存的是 (-score, uri)，heappop 得到最高分（最负值）
        sorted_points = []
        while points:
            neg_score, uri = heapq.heappop(points)
            sorted_points.append((uri, -neg_score))
        sorted_points.reverse()  # 最高分在前

        return sorted_points

    # ------------------------------------------------------------------
    # Step 4: heapq 递归搜索
    # ------------------------------------------------------------------

    async def _recursive_search(
        self,
        query_vector: List[float],
        starting_points: List[Tuple[str, float]],
        user: str,
        space: SpaceType,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """heapq 优先队列驱动的递归搜索。

        参考 OpenViking _recursive_search：
        - 从起始点开始，按分数高低探索
        - 搜索每个目录的子节点（所有 level）
        - L0/L1 继续深入，L2 收集为结果
        - 收敛检测提前退出
        """
        owner_space = user if space == SpaceType.USER else f"agent:{user}"

        collected_by_uri: Dict[str, Dict[str, Any]] = {}
        dir_queue: List[Tuple[float, str]] = []  # min-heap: (-score, uri)
        visited: Set[str] = set()
        prev_topk_uris: Set[str] = set()
        convergence_rounds = 0
        round_count = 0

        alpha = self.SCORE_PROPAGATION_ALPHA

        # 初始化优先队列
        for uri, score in starting_points:
            heapq.heappush(dir_queue, (-score, uri))

        while dir_queue and round_count < self.MAX_TRAVERSAL_ROUNDS:
            round_count += 1

            neg_score, current_uri = heapq.heappop(dir_queue)
            current_score = -neg_score

            if current_uri in visited:
                continue
            visited.add(current_uri)

            # 搜索当前 category 目录下的子节点（所有 level）
            try:
                results = await self._chromadb.search_similar_memories(
                    owner_space=owner_space,
                    category_uri_prefix=current_uri,
                    query_vector=query_vector,
                    limit=max(limit * 2, 20),
                )
            except Exception as e:
                logger.error(
                    f"[HierarchicalRetriever] Search failed for {current_uri}: {e}"
                )
                continue

            if not results:
                continue

            for r in results:
                uri = r.get("uri", "")
                score = r.get("_score", 0.0)
                level = r.get("level", 2)

                # 分数传播：混合子级自身分数与父级分数
                final_score = (
                    alpha * score + (1 - alpha) * current_score
                    if current_score > 0
                    else score
                )

                # 阈值剪枝
                if final_score < self.MIN_SCORE_THRESHOLD:
                    continue

                # 去重：同一 URI 保留最高分
                previous = collected_by_uri.get(uri)
                if previous is None or final_score > previous.get("_final_score", 0):
                    collected_by_uri[uri] = {**r, "_final_score": final_score}

                # L0/L1 → 继续深入（作为目录进一步搜索其子节点）
                # L2 → 终端命中，已收集在 collected_by_uri
                if uri not in visited and level != self.TERMINAL_LEVEL:
                    heapq.heappush(dir_queue, (-final_score, uri))

            # 收敛检测
            current_topk = sorted(
                collected_by_uri.values(),
                key=lambda x: x.get("_final_score", 0),
                reverse=True,
            )[:limit]
            current_topk_uris = {c.get("uri", "") for c in current_topk}

            if current_topk_uris == prev_topk_uris and len(current_topk_uris) >= limit:
                convergence_rounds += 1
                if convergence_rounds >= self.MAX_CONVERGENCE_ROUNDS:
                    logger.info(
                        f"[HierarchicalRetriever] Converged after {round_count} rounds"
                    )
                    break
            else:
                convergence_rounds = 0
                prev_topk_uris = current_topk_uris

        # 按 final_score 降序返回
        collected = sorted(
            collected_by_uri.values(),
            key=lambda x: x.get("_final_score", 0),
            reverse=True,
        )
        return collected[:limit]

    # ------------------------------------------------------------------
    # Step 5: 结果转换
    # ------------------------------------------------------------------

    def _convert_to_matched_contexts(
        self,
        candidates: List[Dict[str, Any]],
    ) -> List[MatchedContext]:
        """将搜索候选转换为 MatchedContext 列表。"""
        results: List[MatchedContext] = []

        for c in candidates:
            score = c.get("_final_score", c.get("_score", 0.0))
            level = c.get("level", 2)

            results.append(
                MatchedContext(
                    uri=c.get("uri", ""),
                    context_type=ContextType.MEMORY,
                    level=level,
                    abstract=c.get("abstract", ""),
                    overview=c.get("overview", None),
                    category=c.get("category", ""),
                    score=score,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_category_dir(uri: str) -> str:
        """从记忆 URI 提取 category 目录路径。

        "data/user/test_user/memories/preferences/mem_xxx.md"
          → "data/user/test_user/memories/preferences"
        """
        if "/memories/" not in uri:
            return uri
        # 找到 /memories/ 后的部分
        idx = uri.index("/memories/") + len("/memories/")
        rest = uri[idx:]
        # category 是第一个路径段
        if "/" in rest:
            category = rest.split("/")[0]
            return uri[:idx] + category
        return uri

    def _get_category_roots(self, user: str, space: SpaceType) -> List[str]:
        """返回所有 category 根目录 URI。"""
        base = f"data/{space.value}/{user}/memories"
        # 已知的 category 目录
        categories = ["preferences", "entities", "events", "cases", "patterns"]
        return [f"{base}/{cat}" for cat in categories]

    # ------------------------------------------------------------------
    # Session file search (unchanged)
    # ------------------------------------------------------------------

    async def _search_session_files(
        self,
        user: str,
        limit: int,
    ) -> List[MatchedContext]:
        """搜索会话目录中的 .abstract.md 和 .overview.md 文件."""
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
                                score=self.SESSION_BASE_SCORE,
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
                                score=self.SESSION_BASE_SCORE,
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
                                        score=self.SESSION_BASE_SCORE,
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
                                        score=self.SESSION_BASE_SCORE,
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
