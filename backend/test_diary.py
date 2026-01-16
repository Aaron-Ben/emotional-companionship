"""Test script for diary functionality."""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.database import init_db
from app.services.diary_service import DiaryService
from app.services.llms.qwen import QwenLLM
from app.models.diary import DiaryTriggerType


async def test_diary_generation():
    """Test diary generation functionality."""
    print("=== 测试日记功能 ===\n")

    # 初始化数据库
    print("1. 初始化数据库...")
    init_db()
    print("✓ 数据库初始化成功\n")

    # 创建服务实例
    print("2. 创建服务实例...")
    diary_service = DiaryService()
    llm = QwenLLM()
    print("✓ 服务实例创建成功\n")

    # 测试生成日记
    print("3. 生成测试日记...")
    try:
        diary = await diary_service.generate_diary(
            llm=llm,
            character_id="sister_001",
            user_id="user_default",
            conversation_summary="今天哥哥跟我说他涨工资了，他看起来好开心！我也为他感到高兴，我们聊了很多关于未来的计划。哥哥说要请我吃好吃的来庆祝～",
            trigger_type=DiaryTriggerType.IMPORTANT_EVENT,
            emotions=["happy", "excited"],
            context={}
        )

        print(f"✓ 日记生成成功！")
        print(f"  - ID: {diary.id}")
        print(f"  - 日期: {diary.date}")
        print(f"  - 触发类型: {diary.trigger_type}")
        print(f"  - 标签: {diary.tags}")
        print(f"  - 内容预览: {diary.content[:100]}...\n")

        # 测试文件存储
        diary_file = diary_service._get_diary_file_path(
            diary.character_id,
            diary.user_id,
            diary.date
        )
        if diary_file.exists():
            print(f"✓ 日记文件已保存: {diary_file}\n")
            with open(diary_file, 'r', encoding='utf-8') as f:
                print("文件内容预览:")
                print("-" * 50)
                print(f.read())
                print("-" * 50)
        else:
            print(f"✗ 日记文件未找到: {diary_file}\n")

    except Exception as e:
        print(f"✗ 日记生成失败: {e}\n")
        import traceback
        traceback.print_exc()

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(test_diary_generation())
