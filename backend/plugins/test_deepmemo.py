"""
DeepMemo Plugin Test Script

This script tests the DeepMemo plugin to verify:
1. Plugin loading
2. stdio protocol execution
3. Tool call processing
4. Result format validation
"""
import asyncio
import sys
from pathlib import Path

# Add project root directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.plugin import plugin_manager


async def test_deepmemo():
    """Test DeepMemo plugin functionality"""

    print("=" * 60)
    print("DeepMemo Plugin Test")
    print("=" * 60)

    # 1. Load plugins
    print("\n=== Loading plugins ===")
    await plugin_manager.load_plugins()

    # 2. Check loaded plugins
    print("\n=== Loaded plugins ===")
    for name, manifest in plugin_manager.plugins.items():
        print(f"- {name}: {manifest.get('displayName')}")

    # 3. Test DeepMemo tool calls
    print("\n=== Testing DeepMemo ===")

    test_cases = [
        {
            "maid": "sister_001",
            "keyword": "你好",
            "windowsize": 3
        },
        {
            "maid": "sister_001",
            "keyword": "哥哥 想念",
            "windowsize": 5
        }
    ]

    for i, args in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Args: {args}")
        result = await plugin_manager.process_tool_call("DeepMemo", args)
        print(f"Result status: {result.get('status')}")

        if result.get('status') == 'success':
            result_content = result.get('result', '')
            print(f"Result preview: {result_content[:200]}...")
            print(f"Full result length: {len(result_content)} characters")
        else:
            print(f"Error: {result.get('error')}")

    # 4. Test with non-existent character (should handle gracefully)
    print("\n--- Test Case: Non-existent character ---")
    result = await plugin_manager.process_tool_call("DeepMemo", {
        "maid": "nonexistent",
        "keyword": "test",
        "windowsize": 3
    })
    print(f"Result status: {result.get('status')}")
    if result.get('status') != 'success':
        print(f"Expected error: {result.get('error')}")

    # 5. Cleanup
    print("\n=== Shutting down plugins ===")
    await plugin_manager.shutdown_all_plugins()
    print("\n=== Test complete ===")


async def test_manifest_capabilities():
    """Test that manifest has proper capabilities field"""
    print("\n=== Testing Manifest Capabilities ===")

    manifest = plugin_manager.get_plugin("DeepMemo")
    if manifest:
        capabilities = manifest.get("capabilities")
        if capabilities:
            print("Capabilities field found!")
            invocation_commands = capabilities.get("invocationCommands", [])
            print(f"Number of invocation commands: {len(invocation_commands)}")
            for cmd in invocation_commands:
                print(f"\nCommand: {cmd.get('command')}")
                print(f"Description length: {len(cmd.get('description', ''))} characters")
                print(f"Example: {cmd.get('example')}")
        else:
            print("WARNING: No capabilities field in manifest!")
    else:
        print("WARNING: DeepMemo plugin not loaded!")


if __name__ == "__main__":
    asyncio.run(test_deepmemo())
    asyncio.run(test_manifest_capabilities())
