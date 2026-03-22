#!/usr/bin/env python3
"""
重新处理指定日记本的标签提取和关联
"""
import asyncio
import json
import re
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.embedding import EmbeddingService
from app.models.database import SessionLocal, TagTable, FileTagTable, DiaryFileTable


def extract_tags(content: str) -> list:
    """从内容中提取标签"""
    tag_lines = re.findall(r'Tag:\s*(.+)$', content, re.MULTILINE | re.IGNORECASE)
    if not tag_lines:
        return []

    all_tags = []
    for line in tag_lines:
        split_tags = re.split(r'[,，、;|｜]', line)
        all_tags.extend(t.strip() for t in split_tags if t.strip())

    # 清理标签
    tags = []
    for tag in all_tags:
        cleaned = re.sub(r'[。.]+$', '', tag).strip()
        if cleaned:
            tags.append(cleaned)

    return list(set(tags))


async def reindex_diary_tags(diary_name: str):
    """重新索引指定日记本的标签"""
    db = SessionLocal()

    try:
        # 获取日记本的所有文件
        files = db.query(DiaryFileTable).filter(DiaryFileTable.diary_name == diary_name).all()
        print(f"📂 Found {len(files)} files in diary '{diary_name}'")

        all_new_tags = set()

        # 遍历所有文件，提取标签
        for file in files:
            # 尝试多种路径格式
            file_path = Path(file.path)
            if not file_path.exists():
                # 尝试相对于 data 目录
                file_path = Path("../data/daily") / diary_name / Path(file.path).name
            if not file_path.exists():
                print(f"  ⚠️ File not found: {file_path}")
                continue

            content = file_path.read_text(encoding='utf-8')
            tags = extract_tags(content)

            if not tags:
                print(f"  ⚠️ No tags in file: {file_path.name}")
                continue

            print(f"  📝 {file_path.name}: {tags}")

            # 删除旧的文件-标签关联
            db.query(FileTagTable).filter(FileTagTable.file_id == file.id).delete()

            # 获取或创建标签
            for tag_name in tags:
                all_new_tags.add(tag_name)

                # 查询或创建标签
                tag_obj = db.query(TagTable).filter(TagTable.name == tag_name).first()
                if not tag_obj:
                    # 新标签，需要向量化
                    print(f"    🏷️ Creating new tag: {tag_name}")
                    tag_obj = TagTable(name=tag_name, vector=None)
                    db.add(tag_obj)
                    db.flush()  # 立即获取 ID

                # 创建关联
                association = FileTagTable(file_id=file.id, tag_id=tag_obj.id)
                db.add(association)

        # 提交第一次更改
        db.commit()

        # 为没有向量的标签生成向量
        print("🎯 Vectorizing tags without vectors...")
        tags_without_vector = db.query(TagTable).filter(
            TagTable.vector == None,
            TagTable.id.in_(
                db.query(FileTagTable.tag_id).join(DiaryFileTable).filter(
                    DiaryFileTable.diary_name == diary_name
                ).distinct()
            )
        ).all()

        if tags_without_vector:
            print(f"   Found {len(tags_without_vector)} tags needing vectorization")
            tag_names = [t.name for t in tags_without_vector]
            async with EmbeddingService() as embedding_service:
                vectors = await embedding_service.get_embeddings_batch(tag_names)

            for tag, vector in zip(tags_without_vector, vectors):
                if vector:
                    tag.vector = json.dumps(vector)
                    print(f"   ✅ Vectorized: {tag.name}")

        # 提交向量更改
        db.commit()
        print(f"✅ Updated tag associations for diary '{diary_name}'")

        # 统计结果
        total_associations = db.query(FileTagTable).join(DiaryFileTable).filter(
            DiaryFileTable.diary_name == diary_name
        ).count()
        print(f"📊 Total tag associations: {total_associations}")

        # 显示该日记本使用的标签
        used_tags = db.query(TagTable).join(FileTagTable).join(DiaryFileTable).filter(
            DiaryFileTable.diary_name == diary_name
        ).distinct().all()
        print(f"🏷️ Tags used in '{diary_name}': {[t.name for t in used_tags]}")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    diary_name = sys.argv[1] if len(sys.argv) > 1 else "Eval"
    asyncio.run(reindex_diary_tags(diary_name))
