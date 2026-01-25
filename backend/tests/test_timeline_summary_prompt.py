"""Test script for TIMELINE_SUMMARY_PROMPT using real data from database.

This script tests the timeline summary prompt with actual future events from the database.
Run with: python tests/test_timeline_summary_prompt.py

Results will be saved to: tests/timeline_summary_results.txt
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from app.services.llms.base import LLMBase
from app.services.temporal.prompt import get_timeline_summary_prompt
from app.services.temporal.retriever import EventRetriever
from app.services.temporal.models import GetEventsRequest

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Output file for results
OUTPUT_FILE = Path(__file__).parent / "timeline_summary_results.txt"


def get_llm() -> LLMBase:
    """Get an LLM instance based on environment configuration."""
    llm_provider = os.getenv("LLM_PROVIDER", "deepseek")

    if llm_provider == "qwen":
        from app.services.llms.qwen import QwenLLM
        from app.configs.llms.qwen import QwenConfig

        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY not set")

        config = QwenConfig(
            api_key=api_key,
            qwen_base_url=os.getenv("QWEN_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        )
        return QwenLLM(config)
    else:  # deepseek
        from app.services.llms.deepseek import DeepSeekLLM
        from app.configs.llms.deepseek import DeepSeekConfig

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not set")

        config = DeepSeekConfig(
            api_key=api_key,
            deepseek_base_url=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com"),
        )
        return DeepSeekLLM(config)


def format_events_for_prompt(events) -> str:
    """Format events into a string for the LLM prompt."""
    if not events:
        return "暂无记录的未来事件。"

    lines = []
    current_date = None

    for event in events:
        # Parse the event_date
        event_date = event.event_date

        # Check if there's a time component
        if ' ' in event_date:
            date_part, time_part = event_date.split(' ', 1)
        else:
            date_part = event_date
            time_part = None

        # Format date for display
        try:
            if ' ' in date_part:
                dt = datetime.strptime(date_part, '%Y-%m-%d')
            else:
                dt = datetime.strptime(date_part, '%Y-%m-%d')
            date_str = dt.strftime('%Y-%m-%d')
        except:
            date_str = date_part

        # Add date header if changed
        if date_str != current_date:
            lines.append(f"\n{date_str}")
            current_date = date_str

        # Format time
        if time_part:
            lines.append(f"{time_part} - {event.title}")
        else:
            lines.append(f"{event.title}")

    return "\n".join(lines)


def print_and_save(title: str, content: str, output_file):
    """Print to console and save to file."""
    separator = "=" * 80

    # Print to console
    print(f"\n{separator}")
    print(f"  {title}")
    print(f"{separator}")
    print(f"\n{content}\n")

    # Save to file
    output_file.write(f"\n{separator}\n")
    output_file.write(f"  {title}\n")
    output_file.write(f"{separator}\n\n")
    output_file.write(f"{content}\n\n")


def get_test_character_and_user():
    """Get character_id and user_id for testing."""
    # Try to get from environment first
    character_id = os.getenv("TEST_CHARACTER_ID")
    user_id = os.getenv("TEST_USER_ID", "user_default")

    if not character_id:
        # Try to get from database
        from app.models.database import SessionLocal, FutureEventTable

        db = SessionLocal()
        try:
            # Get the most recent event with its character_id and user_id
            event = db.query(FutureEventTable).order_by(
                FutureEventTable.created_at.desc()
            ).first()

            if event:
                character_id = event.character_id
                user_id = event.user_id
                print(f"从数据库获取到 character_id: {character_id}, user_id: {user_id}")
            else:
                print("数据库中没有未来事件，使用默认值")
                character_id = "char_default"
        finally:
            db.close()

    return character_id, user_id


def test_with_real_events(llm, retriever, character_id: str, user_id: str, output_file, days_ahead: int = 365):
    """Test timeline summary with real events from database."""
    # Get future events for the specified days
    request = GetEventsRequest(
        character_id=character_id,
        user_id=user_id,
        days_ahead=days_ahead
    )

    events = retriever.get_future_events(request)

    if not events:
        print(f"\n⚠️  数据库中没有找到未来事件 (character_id={character_id}, user_id={user_id})")
        print("请先通过对话创建一些未来事件，然后再运行此测试。\n")
        return None

    print(f"\n从数据库获取到 {len(events)} 个未来事件")

    # Print raw events to console
    print("\n" + "-" * 60)
    print(f"原始事件列表（来自数据库，未来{days_ahead}天）：")
    print("-" * 60)
    for event in events:
        print(f"  [{event.event_date}] {event.title}")
    print("-" * 60)

    # Format events for prompt
    events_text = format_events_for_prompt(events)
    input_text = f"""以下是用户全部的未来事件列表：

{events_text}

请根据这些事件生成时间线总结。"""

    # Print input to LLM
    print("\n发送给 LLM 的输入：")
    print("-" * 60)
    print(input_text)
    print("-" * 60 + "\n")

    # Call LLM
    prompt = get_timeline_summary_prompt()
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": input_text},
    ]

    response = llm.generate_response(messages=messages)
    print_and_save("LLM 生成的总结：", response, output_file)
    return response


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  TIMELINE_SUMMARY_PROMPT 测试（使用真实数据库数据）")
    print("  LLM Provider: " + os.getenv("LLM_PROVIDER", "deepseek"))
    print("  测试时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)
    print(f"\n结果将保存到: {OUTPUT_FILE}\n")

    try:
        llm = get_llm()
        retriever = EventRetriever()

        # Get character_id and user_id
        character_id, user_id = get_test_character_and_user()

        # Open output file
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            # Write header
            f.write("=" * 80 + "\n")
            f.write("  TIMELINE_SUMMARY_PROMPT 测试结果（真实数据）\n")
            f.write(f"  LLM Provider: {os.getenv('LLM_PROVIDER', 'deepseek')}\n")
            f.write(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"  Character ID: {character_id}\n")
            f.write(f"  User ID: {user_id}\n")
            f.write("=" * 80 + "\n\n")

            # Run test with real data
            response = test_with_real_events(llm, retriever, character_id, user_id, f)

            if response is None:
                f.write("\n⚠️  数据库中没有未来事件，无法完成测试。\n")
                f.write("请先通过对话创建一些未来事件。\n\n")

        print("=" * 80)
        print("  测试完成！")
        print(f"  结果已保存到: {OUTPUT_FILE}")
        print("=" * 80 + "\n")

    except ValueError as e:
        print(f"\n❌ 错误: {e}")
        print("\n请确保设置了以下环境变量:")
        print("  - DEEPSEEK_API_KEY 或 DASHSCOPE_API_KEY")
        print("  - LLM_PROVIDER (可选，默认为 deepseek)")
        return 1
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
