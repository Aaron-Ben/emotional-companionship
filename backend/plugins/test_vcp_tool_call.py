#!/usr/bin/env python3
"""
Test script for VCP tool call parser.
Tests the parser with various input formats.
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from plugins.tool_call_parser import ToolCallParser, ToolCall


def test_simple_tool_call():
    """Test simple tool call parsing."""
    content = '''
这是普通回复。

<<<[TOOL_REQUEST]>>>
tool_name:「始」DeepMemo「末」,
maid:「始」sister_001「末」,
keyword:「始」哥哥 想念「末」,
windowsize:「始」3「末」
<<<[END_TOOL_REQUEST]>>>

继续回复。
'''

    calls = ToolCallParser.parse(content)
    assert len(calls) == 1, f"Expected 1 call, got {len(calls)}"
    assert calls[0].name == "DeepMemo", f"Expected 'DeepMemo', got '{calls[0].name}'"
    assert calls[0].args['maid'] == "sister_001", f"Expected 'sister_001', got '{calls[0].args.get('maid')}'"
    assert calls[0].args['keyword'] == "哥哥 想念", f"Expected '哥哥 想念', got '{calls[0].args.get('keyword')}'"
    assert calls[0].args['windowsize'] == "3", f"Expected '3', got '{calls[0].args.get('windowsize')}'"

    print("✓ test_simple_tool_call passed")


def test_multiple_tool_calls():
    """Test multiple tool calls in one response."""
    content = '''
<<<[TOOL_REQUEST]>>>
tool_name:「始」DeepMemo「末」,
maid:「始」sister_001「末」,
keyword:「始」回忆「末」
<<<[END_TOOL_REQUEST]>>>

<<<[TOOL_REQUEST]>>>
tool_name:「始」OtherTool「末」,
param1:「始」value1「末」
<<<[END_TOOL_REQUEST]>>>
'''

    calls = ToolCallParser.parse(content)
    assert len(calls) == 2, f"Expected 2 calls, got {len(calls)}"
    assert calls[0].name == "DeepMemo"
    assert calls[1].name == "OtherTool"

    print("✓ test_multiple_tool_calls passed")


def test_archery_call():
    """Test async (archery) tool call."""
    content = '''
<<<[TOOL_REQUEST]>>>
tool_name:「始」BackgroundTask「末」,
archery:「始」true「末」,
data:「始」some data「末」
<<<[END_TOOL_REQUEST]>>>
'''

    calls = ToolCallParser.parse(content)
    assert len(calls) == 1, f"Expected 1 call, got {len(calls)}"
    assert calls[0].archery == True, f"Expected archery=True, got {calls[0].archery}"

    print("✓ test_archery_call passed")


def test_no_tool_call():
    """Test content without tool calls."""
    content = '''
这是一个普通的回复，没有工具调用。
用户只是想聊聊天。
'''

    calls = ToolCallParser.parse(content)
    assert len(calls) == 0, f"Expected 0 calls, got {len(calls)}"

    print("✓ test_no_tool_call passed")


def test_contains_tool_call():
    """Test the contains_tool_call helper."""
    assert ToolCallParser.contains_tool_call("<<<[TOOL_REQUEST]>>>") == True
    assert ToolCallParser.contains_tool_call("No tool call here") == False
    assert ToolCallParser.contains_tool_call("") == False

    print("✓ test_contains_tool_call passed")


def test_separate_calls():
    """Test separating normal and archery calls."""
    calls = [
        ToolCall(name="Tool1", args={}, archery=False),
        ToolCall(name="Tool2", args={}, archery=True),
        ToolCall(name="Tool3", args={}, archery=False),
        ToolCall(name="Tool4", args={}, archery=True),
    ]

    separated = ToolCallParser.separate(calls)
    assert len(separated['normal']) == 2, f"Expected 2 normal calls, got {len(separated['normal'])}"
    assert len(separated['archery']) == 2, f"Expected 2 archery calls, got {len(separated['archery'])}"

    print("✓ test_separate_calls passed")


def main():
    """Run all tests."""
    print("Running VCP tool call parser tests...\n")

    try:
        test_simple_tool_call()
        test_multiple_tool_calls()
        test_archery_call()
        test_no_tool_call()
        test_contains_tool_call()
        test_separate_calls()

        print("\n✓ All tests passed!")
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
