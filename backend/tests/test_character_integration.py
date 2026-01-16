"""Integration test for character system.

This test demonstrates the character system functionality without requiring LLM API calls.
"""

import asyncio
from app.services.character_service import CharacterService
from app.services.chat_service import ChatService
from app.models.character import UserCharacterPreference
from app.schemas.message import ChatRequest
from datetime import datetime
from app.services.llms.base import LLMBase
from typing import List, Dict, Optional


class MockLLM(LLMBase):
    """Mock LLM for testing without API calls."""

    def generate_response(
        self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None, tool_choice: str = "auto", **kwargs
    ) -> str:
        """Generate a mock response."""
        # Extract system prompt to show it was used
        system_prompt = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_message = next((m["content"] for m in messages if m["role"] == "user"), "")

        # Show that the system prompt includes character instructions
        if "哥哥" in system_prompt:
            return f"哥哥回来啦！{user_message}（这是模拟回复，实际会调用LLM）"
        return f"收到：{user_message}"

    def generate_response_stream(
        self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None, tool_choice: str = "auto", **kwargs
    ):
        """Generate a mock streaming response."""
        response = self.generate_response(messages, tools, tool_choice, **kwargs)
        for char in response:
            yield char


async def test_character_system():
    """Test the character system end-to-end."""
    print("=" * 70)
    print("角色系统集成测试")
    print("=" * 70)
    print()

    # Initialize services
    character_service = CharacterService()
    mock_llm = MockLLM()
    chat_service = ChatService(llm=mock_llm, character_service=character_service)

    # Test 1: List characters
    print("测试 1: 列出所有角色")
    print("-" * 70)
    characters = character_service.list_characters()
    print(f"✓ 已加载 {len(characters)} 个角色")
    for char in characters:
        print(f"  - {char.name} ({char.character_id}): {char.identity.description[:50]}...")
    print()

    # Test 2: Get specific character
    print("测试 2: 获取特定角色")
    print("-" * 70)
    sister = character_service.get_character("sister_001")
    print(f"✓ 角色名称: {sister.name}")
    print(f"✓ 基础昵称: {sister.base_nickname}")
    print(f"✓ 性格特征: {[t.value for t in sister.identity.personality_traits]}")
    print()

    # Test 3: Generate base system prompt
    print("测试 3: 生成基础系统提示词")
    print("-" * 70)
    base_prompt = character_service.generate_system_prompt("sister_001")
    print(f"✓ 系统提示词长度: {len(base_prompt)} 字符")
    print(f"✓ 包含'哥哥': {'是' if '哥哥' in base_prompt else '否'}")
    print(f"✓ 包含情感支持说明: {'是' if '情感支持' in base_prompt else '否'}")
    print()

    # Test 4: User preferences
    print("测试 4: 应用用户偏好")
    print("-" * 70)
    preferences = UserCharacterPreference(
        user_id="test_user",
        character_id="sister_001",
        nickname="亲爱的哥哥",
        style_level=0.85,
        custom_instructions="特别喜欢聊游戏",
        relationship_notes="关系很亲密",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    personalized_prompt = character_service.generate_system_prompt(
        "sister_001", user_preferences=preferences
    )
    print(f"✓ 自定义昵称已应用: {'是' if '亲爱的哥哥' in personalized_prompt else '否'}")
    print(f"✓ 自定义说明已应用: {'是' if '游戏' in personalized_prompt else '否'}")
    print(f"✓ 风格调整已应用: {'是' if '格外顽皮' in personalized_prompt or '格外' in personalized_prompt else '否'}")
    print()

    # Test 5: Context-aware modifications
    print("测试 5: 上下文感知调整")
    print("-" * 70)
    angry_context = {
        "user_mood": {"primary_emotion": "angry", "confidence": 0.8},
        "should_avoid_argument": True
    }
    context_prompt = character_service.generate_system_prompt(
        "sister_001", context=angry_context
    )
    print(f"✓ 愤怒用户上下文已应用: {'是' if '避免冲突' in context_prompt else '否'}")
    print(f"✓ 额外支持说明已应用: {'是' if '额外支持' in context_prompt else '否'}")
    print()

    # Test 6: Emotion detection
    print("测试 6: 情绪检测")
    print("-" * 70)
    test_messages = [
        ("我回来了", "neutral"),
        ("今天好累啊", "sad"),
        ("气死我了！", "angry"),
        ("太开心了！", "happy"),
    ]
    for msg, expected in test_messages:
        emotion = chat_service._detect_emotion(msg)
        status = "✓" if emotion.primary_emotion == expected else "✗"
        print(f"{status} '{msg}' -> {emotion.primary_emotion} (期望: {expected})")
    print()

    # Test 7: Chat response generation
    print("测试 7: 聊天响应生成")
    print("-" * 70)
    request = ChatRequest(
        message="我回来了",
        character_id="sister_001"
    )
    response = await chat_service.chat(request)
    print(f"✓ 用户消息: {request.message}")
    print(f"✓ 角色响应: {response.message}")
    print(f"✓ 检测到的情绪: {response.emotion_detected.primary_emotion}")
    print()

    # Test 8: Conversation starters
    print("测试 8: 对话开场")
    print("-" * 70)
    starter = character_service.get_conversation_starter("sister_001")
    print(f"✓ 对话开场: {starter}")
    print()

    print("=" * 70)
    print("所有测试完成！✓")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_character_system())
