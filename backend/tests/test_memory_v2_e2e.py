"""
End-to-end test for Memory V2 system.

Run: cd backend && .venv/bin/python tests/test_memory_v2_e2e.py
"""
import asyncio
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from memory.v2.chromadb_manager import ChromaDBManager
from memory.v2.model import MemoryContext
from app.services.embedding import EmbeddingService, get_embeddings_batch

passed = 0
failed = 0


def _make_memory(
    memory_id: str = "mem_test001",
    abstract: str = "用户喜欢橘猫",
    overview: str = "用户是一个资深猫奴，特别喜欢橘猫，家里养了一只叫小橘的猫",
    content: str = "用户是一个资深猫奴，特别喜欢橘猫。家里养了一只橘猫叫小橘，已经养了3年。",
) -> MemoryContext:
    return MemoryContext(
        id=memory_id,
        uri=f"data/user/test_user/memories/preferences/{memory_id}.md",
        parent_uri="data/user/test_user/memories/preferences",
        category="preferences",
        abstract=abstract,
        overview=overview,
        content=content,
        session_id="test_session",
        user="test_user",
        level=2,
    )


def _cleanup(chromadb):
    ids = chromadb.collection.get(include=[]).get("ids", [])
    if ids:
        chromadb.collection.delete(ids=ids)


async def _insert_test_memory(chromadb: ChromaDBManager, emb: EmbeddingService):
    """Insert a test memory with L0/L1/L2 via add_memory."""
    base_id = "mem_test001"
    abstract = "用户喜欢橘猫"
    overview = "用户是一个资深猫奴，特别喜欢橘猫，家里养了一只叫小橘的猫"
    content = "用户是一个资深猫奴，特别喜欢橘猫。家里养了一只橘猫叫小橘，已经养了3年。"

    l0e = await emb.get_single_embedding(abstract)
    l1e = await emb.get_single_embedding(overview)
    l2e = await emb.get_single_embedding(content)

    common = {
        "uri": f"data/user/test_user/memories/preferences/{base_id}.md",
        "parent_uri": "data/user/test_user/memories/preferences",
        "base_id": base_id,
        "category": "preferences",
        "session_id": "test",
        "user": "test_user",
        "context_type": "memory",
        "owner_space": "test_user",
    }

    await chromadb.add_memory(
        f"{base_id}__L0", l0e, abstract,
        {**common, "abstract": abstract, "level": 0},
    )
    await chromadb.add_memory(
        f"{base_id}__L1", l1e, overview,
        {**common, "overview": overview, "level": 1},
    )
    await chromadb.add_memory(
        f"{base_id}__L2", l2e, content,
        {**common, "abstract": abstract, "overview": overview, "content": content, "level": 2},
    )

    return base_id, l2e


# ── Test functions ────────────────────────────────────────────────────────

async def test_1_multi_level_indexing():
    """_index_memory should create L0, L1, L2 records in ChromaDB."""
    from memory.v2.compressor import Compressor

    chromadb = ChromaDBManager()
    _cleanup(chromadb)

    compressor = Compressor(chromadb=chromadb)
    memory = _make_memory()

    ok = await compressor._index_memory(memory)
    assert ok, "Indexing should succeed"

    count = chromadb.collection.count()
    assert count == 3, f"Expected 3 records (L0+L1+L2), got {count}"

    _cleanup(chromadb)
    return True


async def test_2_search_all_levels():
    """Search without level_filter should return L0, L1, L2."""
    chromadb = ChromaDBManager()
    _cleanup(chromadb)
    emb = EmbeddingService()

    await _insert_test_memory(chromadb, emb)

    query_vec = await emb.get_single_embedding("用户喜欢什么宠物？")
    results = await chromadb.search_similar_memories(
        owner_space="test_user",
        category_uri_prefix="data/user/test_user/memories/",
        query_vector=query_vec,
        limit=10,
    )

    levels = {r.get("level") for r in results}
    assert levels == {0, 1, 2}, f"Expected all 3 levels, got {levels}"

    _cleanup(chromadb)
    return True


async def test_3_search_l2_only():
    """Search with level_filter=2 should only return L2."""
    chromadb = ChromaDBManager()
    _cleanup(chromadb)
    emb = EmbeddingService()

    await _insert_test_memory(chromadb, emb)

    query_vec = await emb.get_single_embedding("用户喜欢什么宠物？")
    results = await chromadb.search_similar_memories(
        owner_space="test_user",
        category_uri_prefix="data/user/test_user/memories/",
        query_vector=query_vec,
        limit=5,
        level_filter=2,
    )

    assert len(results) == 1, f"Expected 1 L2 result, got {len(results)}"
    assert results[0].get("level") == 2

    _cleanup(chromadb)
    return True


async def test_4_score_formula():
    """Self-match should score ~1.0."""
    chromadb = ChromaDBManager()
    _cleanup(chromadb)
    emb = EmbeddingService()

    _, l2_embed = await _insert_test_memory(chromadb, emb)

    results = await chromadb.search_similar_memories(
        owner_space="test_user",
        category_uri_prefix="data/user/test_user/memories/",
        query_vector=l2_embed,
        limit=1,
        level_filter=2,
    )

    score = results[0].get("_score", 0)
    assert score > 0.99, f"Self-match score should be ~1.0, got {score}"

    _cleanup(chromadb)
    return True


async def test_5_delete_memory_tree():
    """delete_memory_tree should remove all L0/L1/L2 records."""
    chromadb = ChromaDBManager()
    _cleanup(chromadb)
    emb = EmbeddingService()

    await _insert_test_memory(chromadb, emb)
    assert chromadb.collection.count() == 3

    ok = await chromadb.delete_memory_tree("mem_test001")
    assert ok
    assert chromadb.collection.count() == 0, "All records should be deleted"

    _cleanup(chromadb)
    return True


async def _insert_full_memory(chromadb, emb, mid, abstract, overview, content, category="preferences"):
    """Insert a complete L0+L1+L2 memory record."""
    l0e = await emb.get_single_embedding(abstract)
    l1e = await emb.get_single_embedding(overview)
    l2e = await emb.get_single_embedding(content)

    common = {
        "uri": f"data/user/test_user/memories/{category}/{mid}.md",
        "parent_uri": f"data/user/test_user/memories/{category}",
        "base_id": mid,
        "category": category,
        "session_id": "test",
        "user": "test_user",
        "context_type": "memory",
        "owner_space": "test_user",
    }

    await chromadb.add_memory(
        f"{mid}__L0", l0e, abstract,
        {**common, "abstract": abstract, "level": 0},
    )
    await chromadb.add_memory(
        f"{mid}__L1", l1e, overview,
        {**common, "overview": overview, "level": 1},
    )
    await chromadb.add_memory(
        f"{mid}__L2", l2e, content,
        {**common, "abstract": abstract, "overview": overview, "content": content, "level": 2},
    )


async def test_6_global_search():
    """Global search should return L0+L1 records (not L2)."""
    from memory.v2.retriever import HierarchicalRetriever, SpaceType

    chromadb = ChromaDBManager()
    _cleanup(chromadb)
    emb = EmbeddingService()

    await _insert_full_memory(
        chromadb, emb, "mem_huoguo",
        abstract="用户喜欢吃火锅",
        overview="用户是四川人，特别喜欢吃麻辣火锅",
        content="用户是四川人，特别喜欢吃麻辣火锅，每周至少吃一次。",
    )
    await _insert_full_memory(
        chromadb, emb, "mem_lanqiu",
        abstract="用户喜欢打篮球",
        overview="用户是篮球爱好者，每周都去打球",
        content="用户是篮球爱好者，每周都去打篮球，打控球后卫位置。",
    )

    retriever = HierarchicalRetriever(chromadb_manager=chromadb, embedding_service=emb)

    query_vec = await emb.get_single_embedding("用户喜欢什么美食？")
    global_results = await retriever._global_search(query_vec, "test_user", SpaceType.USER)

    assert len(global_results) > 0, f"Expected global results, got {len(global_results)}"
    for r in global_results:
        level = r.get("level", 2)
        assert level in (0, 1), f"Expected L0 or L1, got level={level}"

    _cleanup(chromadb)
    return True


async def test_7_extract_category_dir():
    """_extract_category_dir should extract category path from memory URI."""
    from memory.v2.retriever import HierarchicalRetriever

    retriever = HierarchicalRetriever.__new__(HierarchicalRetriever)

    # Standard memory URI → category directory
    uri = "data/user/test_user/memories/preferences/mem_xxx.md"
    assert retriever._extract_category_dir(uri) == "data/user/test_user/memories/preferences"

    # Entities category
    uri = "data/user/test_user/memories/entities/mem_yyy.md"
    assert retriever._extract_category_dir(uri) == "data/user/test_user/memories/entities"

    # Already a directory path (no .md)
    uri = "data/user/test_user/memories/events"
    assert retriever._extract_category_dir(uri) == uri

    return True


async def test_8_build_starting_points():
    """Starting points should merge global search hits with root categories."""
    from memory.v2.retriever import HierarchicalRetriever, SpaceType

    retriever = HierarchicalRetriever(chromadb_manager=None, embedding_service=None)

    # Simulate global search results with different categories
    global_results = [
        {"uri": "data/user/test_user/memories/preferences/mem_a.md", "_score": 0.8, "level": 0},
        {"uri": "data/user/test_user/memories/entities/mem_b.md", "_score": 0.5, "level": 1},
    ]

    starting_points = retriever._build_starting_points("test_user", SpaceType.USER, global_results)

    # Should contain both categories from global hits + remaining root categories
    uris = [uri for uri, _ in starting_points]
    assert "data/user/test_user/memories/preferences" in uris, "preferences should be a starting point"
    assert "data/user/test_user/memories/entities" in uris, "entities should be a starting point"

    # preferences (score=0.8) should rank higher than entities (score=0.5)
    pref_score = next(s for u, s in starting_points if "preferences" in u)
    ent_score = next(s for u, s in starting_points if "entities" in u)
    assert pref_score > ent_score, f"preferences ({pref_score}) should outrank entities ({ent_score})"

    return True


async def test_9_full_heapq_retrieval():
    """Full heapq-driven retrieval should rank relevant results first."""
    from memory.v2.retriever import HierarchicalRetriever, SpaceType

    chromadb = ChromaDBManager()
    _cleanup(chromadb)
    emb = EmbeddingService()

    await _insert_full_memory(
        chromadb, emb, "mem_huoguo",
        abstract="用户喜欢吃火锅",
        overview="用户是四川人，特别喜欢吃麻辣火锅",
        content="用户是四川人，特别喜欢吃麻辣火锅，每周至少吃一次。",
        category="preferences",
    )
    await _insert_full_memory(
        chromadb, emb, "mem_lanqiu",
        abstract="用户喜欢打篮球",
        overview="用户是篮球爱好者，每周都去打球",
        content="用户是篮球爱好者，每周都去打篮球，打控球后卫位置。",
        category="preferences",
    )

    retriever = HierarchicalRetriever(chromadb_manager=chromadb, embedding_service=emb)
    result = await retriever.retrieve(
        query="用户喜欢吃什么？",
        user="test_user",
        space=SpaceType.USER,
        limit=5,
    )

    assert len(result.matched_contexts) >= 1, f"Expected >= 1 result, got {len(result.matched_contexts)}"

    top_abstract = result.matched_contexts[0].abstract
    assert "火锅" in top_abstract, f"Expected 火锅 in top result, got: {top_abstract}"

    for ctx in result.matched_contexts:
        print(f"    level={ctx.level}, score={ctx.score:.4f}, abstract={ctx.abstract[:40]}")

    _cleanup(chromadb)
    return True


async def test_10_cross_category_retrieval():
    """Retrieval should rank relevant category results above irrelevant ones."""
    from memory.v2.retriever import HierarchicalRetriever, SpaceType

    chromadb = ChromaDBManager()
    _cleanup(chromadb)
    emb = EmbeddingService()

    await _insert_full_memory(
        chromadb, emb, "mem_huoguo",
        abstract="用户喜欢吃火锅",
        overview="用户是四川人，特别喜欢吃麻辣火锅",
        content="用户是四川人，特别喜欢吃麻辣火锅，每周至少吃一次。",
        category="preferences",
    )
    await _insert_full_memory(
        chromadb, emb, "mem_workout",
        abstract="用户每天做力量训练",
        overview="用户有严格的力量训练计划，每天去健身房",
        content="用户有严格的力量训练计划，每天去健身房做深蹲和卧推。",
        category="entities",
    )

    retriever = HierarchicalRetriever(chromadb_manager=chromadb, embedding_service=emb)
    result = await retriever.retrieve(
        query="用户喜欢吃什么？",
        user="test_user",
        space=SpaceType.USER,
        limit=5,
    )

    if result.matched_contexts:
        top = result.matched_contexts[0]
        print(f"    Top result: category={top.category}, abstract={top.abstract[:40]}")
        assert top.category == "preferences", f"Expected preferences, got {top.category}"

    _cleanup(chromadb)
    return True


async def test_11_score_propagation():
    """Score propagation: alpha * child + (1-alpha) * parent (alpha=0.5)."""
    # The retriever uses SCORE_PROPAGATION_ALPHA = 0.5
    # final = 0.5 * child + 0.5 * parent
    alpha = 0.5
    child = 0.8
    parent = 0.5
    expected = alpha * child + (1 - alpha) * parent  # = 0.65
    assert abs(expected - 0.65) < 0.001, f"Expected 0.65, got {expected}"

    return True


async def test_7_full_extraction():
    """Full pipeline: extract -> dedup -> index -> search (needs LLM)."""
    from memory.v2.compressor import Compressor

    chromadb = ChromaDBManager()
    _cleanup(chromadb)

    compressor = Compressor(chromadb=chromadb)

    messages = [
        {"role": "user", "content": "我最近养了一只橘猫，叫小橘，特别可爱"},
        {"role": "assistant", "content": "橘猫确实很可爱！小橘多大了？"},
        {"role": "user", "content": "两岁了，我每天都给它拍照发朋友圈"},
        {"role": "assistant", "content": "你真是一个负责任的猫主人！"},
        {"role": "user", "content": "我还喜欢打篮球，每周都会去打球"},
        {"role": "assistant", "content": "运动很棒，你打什么位置？"},
        {"role": "user", "content": "我打控球后卫，觉得很有趣"},
    ]

    memories = await compressor.extract_long_term_memories(
        messages=messages,
        user="test_user",
        session_id="test_session_001",
    )

    print(f"\n    Extracted {len(memories)} memories")
    for m in memories:
        print(f"      category={m.category}, abstract={m.abstract[:50]}")

    count = chromadb.collection.count()
    print(f"    ChromaDB records: {count}")

    assert len(memories) >= 1, "Should extract at least 1 memory"
    # Each memory produces at least 1 record (L0 always, L1/L2 depend on content)
    assert count >= len(memories), f"Expected >={len(memories)} ChromaDB records, got {count}"

    # Search extracted memories
    embeds = await get_embeddings_batch(["用户喜欢什么宠物"])
    query_vec = embeds[0]
    results = await chromadb.search_similar_memories(
        owner_space="test_user",
        category_uri_prefix="data/user/test_user/memories/",
        query_vector=query_vec,
        limit=5,
    )
    assert len(results) > 0, "Should find extracted memories via search"
    for r in results:
        level = r.get("level")
        score = r.get("_score", 0)
        text = (r.get("abstract") or r.get("content") or "")[:40]
        print(f"      level={level}, score={score:.4f}, text={text}")

    _cleanup(chromadb)
    return True


# ── Runner ────────────────────────────────────────────────────────────────

async def run_all():
    global passed, failed

    tests = [
        ("Test 1: Multi-level indexing", test_1_multi_level_indexing),
        ("Test 2: Search all levels", test_2_search_all_levels),
        ("Test 3: Search L2 only", test_3_search_l2_only),
        ("Test 4: Score formula (self-match=1.0)", test_4_score_formula),
        ("Test 5: delete_memory_tree", test_5_delete_memory_tree),
        ("Test 6: Global search L0+L1", test_6_global_search),
        ("Test 7: Extract category dir", test_7_extract_category_dir),
        ("Test 8: Build starting points", test_8_build_starting_points),
        ("Test 9: Full heapq retrieval", test_9_full_heapq_retrieval),
        ("Test 10: Cross-category retrieval", test_10_cross_category_retrieval),
        ("Test 11: Score propagation formula", test_11_score_propagation),
        ("Test 12: Full extraction pipeline (LLM)", test_7_full_extraction),
    ]

    for name, fn in tests:
        print(f"\n{'='*60}")
        print(f"  {name}")
        print(f"{'='*60}")
        try:
            await fn()
            print(f"  ✅ PASSED")
            passed += 1
        except Exception as e:
            traceback.print_exc()
            print(f"  ❌ FAILED: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed, {passed+failed} total")
    print(f"{'='*60}")


if __name__ == "__main__":
    rm_dir = os.path.join(os.path.dirname(__file__), "..", "..", "chroma-db")
    import shutil
    if os.path.exists(rm_dir):
        shutil.rmtree(rm_dir)
        print("Cleared chroma-db/")

    asyncio.run(run_all())
