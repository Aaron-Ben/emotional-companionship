"""测试 extract_long_term_memories 方法 - 使用真实 LLM"""
import pytest

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


@pytest.fixture
def chromadb():
    from memory.v2.chromadb_manager import ChromaDBManager
    return ChromaDBManager()


@pytest.fixture
def compressor(chromadb):
    from memory.v2.compressor import Compressor
    return Compressor(chromadb=chromadb)


def test_chunk_text():
    """测试文本分块功能"""
    from memory.v2.compressor import Compressor

    # 短文本直接返回
    text = "short text"
    chunks = Compressor._chunk_text(text, chunk_size=100, overlap=10)
    assert chunks == [text]

    # 长文本分块
    long_text = "a" * 200
    chunks = Compressor._chunk_text(long_text, chunk_size=100, overlap=20)
    assert len(chunks) > 1


@pytest.mark.asyncio
async def test_extract_empty_messages(compressor):
    """测试空消息列表"""
    result = await compressor.extract_long_term_memories(
        messages=[],
        user='test_user',
        session_id='test_001'
    )
    assert result == []


@pytest.mark.asyncio
async def test_extract_with_single_message(compressor, chromadb):
    """测试单条消息提取"""
    messages = [
        {'role': 'user', 'content': '我喜欢蓝色'},
    ]

    result = await compressor.extract_long_term_memories(
        messages=messages,
        user='test_user',
        session_id='test_session_001'
    )

    print(f"提取了 {len(result)} 个记忆")
    for mem in result:
        print(f"  - {mem.uri}: {mem.abstract}")

    assert isinstance(result, list)
    assert len(result) > 0

    # 验证 ChromaDB
    search_results = await chromadb.search_similar_memories(
        owner_space='test_user',
        category_uri_prefix='data/user/test_user/memories/preferences/',
        query_vector=[0.0] * 1024,
        limit=5
    )
    print(f"ChromaDB 中有 {len(search_results)} 条记忆")
    assert len(search_results) > 0


@pytest.mark.asyncio
async def test_extract_with_conversation(compressor, chromadb):
    """测试对话提取多个记忆"""
    messages = [
        {'role': 'user', 'content': '我喜欢蓝色和阅读科幻小说'},
        {'role': 'assistant', 'content': '好的，我记住你的爱好'},
    ]

    result = await compressor.extract_long_term_memories(
        messages=messages,
        user='test_user',
        session_id='test_session_002'
    )

    print(f"提取了 {len(result)} 个记忆")
    for mem in result:
        print(f"  - {mem.uri}: {mem.abstract}")

    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_extract_profile_category(compressor, chromadb):
    """测试 Profile 类别记忆"""
    messages = [
        {'role': 'user', 'content': '我叫张三，是一名软件工程师'},
    ]

    result = await compressor.extract_long_term_memories(
        messages=messages,
        user='test_user',
        session_id='test_session_003'
    )

    print(f"Profile 测试: 提取了 {len(result)} 个记忆")
    for mem in result:
        print(f"  - uri: {mem.uri}, category: {mem.category}")

    assert isinstance(result, list)
