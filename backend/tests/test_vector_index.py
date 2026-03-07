"""测试 VectorIndex.process_diary_file 方法

这个脚本测试如何为日记文件建立向量索引。
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.vector_index import VectorIndex, VectorIndexConfig
from app.models.database import init_db, SessionLocal, DiaryFileTable, ChunkTable


async def test_process_diary_file():
    """测试处理单个日记文件"""

    # 初始化数据库
    print("=" * 60)
    print("初始化数据库...")
    init_db()
    print("✅ 数据库初始化完成\n")

    # 创建 VectorIndex 实例
    print("=" * 60)
    print("创建 VectorIndex 实例...")
    config = VectorIndexConfig()
    vector_index = VectorIndex(config)
    print("✅ VectorIndex 实例创建完成\n")

    # 测试参数
    name = "严肃的老师"
    file_path = "2026-03-06-14_32_18.txt"

    print("=" * 60)
    print(f"测试参数:")
    print(f"  日记名称: {name}")
    print(f"  日记文件: {file_path}")
    print("=" * 60)
    print()

    # 执行处理
    print("开始处理日记文件...")
    result = await vector_index.process_diary_file(name, file_path)

    # 显示结果
    print()
    print("=" * 60)
    print("处理结果:")
    print("=" * 60)

    if "error" in result:
        print(f"❌ 错误: {result['error']}")
        if "detail" in result:
            print(f"   详情: {result['detail']}")
        if "path" in result:
            print(f"   路径: {result['path']}")
    else:
        print(f"✅ 处理成功!")
        print(f"   文件ID: {result.get('file_id')}")
        print(f"   分块数量: {result.get('chunk_count')}")
        print(f"   日记名称: {result.get('diary_name')}")
        print(f"   是否更新: {result.get('updated')}")
        if result.get('skipped'):
            print(f"   状态: 文件未变更，已跳过")

    print("=" * 60)
    print()

    db = SessionLocal()
    try:
        # 查询日记文件记录
        diary_files = db.query(DiaryFileTable).filter(
            DiaryFileTable.path == file_path
        ).all()

        print(f"找到 {len(diary_files)} 条日记文件记录")

        for file_record in diary_files:
            print(f"\n📄 日记文件 #{file_record.id}:")
            print(f"   路径: {file_record.path}")
            print(f"   日记名称: {file_record.diary_name}")
            print(f"   文件大小: {file_record.size} bytes")
            print(f"   校验和: {file_record.checksum}")
            print(f"   分块数量: {len(file_record.chunks)}")

            # 显示所有分块
            for i, chunk in enumerate(file_record.chunks):
                print(f"\n   📝 分块 #{i+1} (ID: {chunk.id}):")
                print(f"      索引: {chunk.chunk_index}")
                content_preview = chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content
                print(f"      内容预览: {content_preview}")
                has_vector = bool(chunk.vector)
                print(f"      向量: {'✅ 已存储' if has_vector else '❌ 缺失'}")

    finally:
        db.close()

    print()
    print("=" * 60)
    print("向量索引统计:")
    print("=" * 60)

    stats = vector_index.get_stats("严肃的老师")
    if stats:
        print(f"日记本: 严肃的老师")
        print(f"  总向量数: {stats['totalVectors']}")
        print(f"  维度: {stats['dimensions']}")
        print(f"  容量: {stats['capacity']}")
        print(f"  内存使用: {stats['memoryUsage']} bytes")
    else:
        print("❌ 索引未加载或不存在")

    print("=" * 60)

    # 保存索引到磁盘
    print()
    print("保存索引到磁盘...")
    await vector_index.flush_all()
    print("✅ 索引已保存")

    print()
    print("=" * 60)
    print("测试完成! 🎉")
    print("=" * 60)


async def test_sync_all_diaries():
    """测试同步所有日记"""

    print("=" * 60)
    print("批量同步日记测试")
    print("=" * 60)
    print()

    # 初始化数据库
    init_db()

    # 创建 VectorIndex 实例
    config = VectorIndexConfig()
    vector_index = VectorIndex(config)

    # 同步所有日记
    name = "严肃的老师"

    print(f"同步日记 '{name}' 的所有日记...")
    result = await vector_index.sync_character_diaries(name)

    print()
    print("=" * 60)
    print("同步结果:")
    print("=" * 60)
    print(f"  处理: {result['processed']} 个文件")
    print(f"  跳过: {result['skipped']} 个文件")
    print(f"  失败: {result['failed']} 个文件")
    print(f"  总分块: {result['total_chunks']} 个")

    if result['files']:
        print("\n文件详情:")
        for file_info in result['files']:
            status_icon = {
                'processed': '✅',
                'skipped': '⏭️',
                'failed': '❌'
            }.get(file_info['status'], '❓')
            print(f"  {status_icon} {file_info['path']}: {file_info['status']}")
            if 'chunk_count' in file_info:
                print(f"     分块数: {file_info['chunk_count']}")

    print("=" * 60)

    # 保存索引
    await vector_index.flush_all()
    print("✅ 索引已保存")


if __name__ == "__main__":
    import logging

    # 设置日志级别
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "=" * 60)
    print("VectorIndex.process_diary_file 测试")
    print("=" * 60)
    print()

    # 运行单个文件测试
    # asyncio.run(test_process_diary_file())

    print("\n\n")

    # 运行批量同步测试
    asyncio.run(test_sync_all_diaries())
