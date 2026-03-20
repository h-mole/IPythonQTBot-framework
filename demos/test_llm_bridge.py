"""
测试 IPython LLM Bridge 功能

使用方法：
1. 在 IPython 控制台中运行此脚本
2. 或者直接在 Python 环境中测试 Agent 类
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_qt.ipython_llm_bridge import Agent, LLMConfig

def test_basic_chat():
    """测试基本对话功能"""
    print("=" * 60)
    print("测试 1: 基本对话功能")
    print("=" * 60)
    
    # 创建 Agent（使用默认 Kimi 配置）
    agent = Agent()
    
    # 测试对话
    agent.ask("你好，请简单介绍一下自己")
    
    print("\n\n等待响应完成...")
    import time
    time.sleep(2)  # 等待输出完成


def test_history_memory():
    """测试历史记忆功能"""
    print("\n" + "=" * 60)
    print("测试 2: 历史记忆功能")
    print("=" * 60)
    
    agent = Agent()
    
    # 第一轮对话
    agent.ask("我喜欢吃苹果")
    import time
    time.sleep(2)
    
    # 第二轮对话（应该记住第一轮的内容）
    agent.ask("我喜欢吃什么？")
    time.sleep(2)
    
    # 查看历史消息
    print(f"\n当前历史消息数：{len(agent.messages)}")
    for i, msg in enumerate(agent.messages):
        print(f"{i+1}. [{msg['role']}] {msg['content'][:50]}...")


def test_clear_history():
    """测试清除历史功能"""
    print("\n" + "=" * 60)
    print("测试 3: 清除历史功能")
    print("=" * 60)
    
    agent = Agent()
    
    # 先进行一些对话
    agent.ask("你好")
    import time
    time.sleep(1)
    
    print(f"\n清除前消息数：{len(agent.messages)}")
    
    # 清除历史
    agent.clear()
    
    print(f"清除后消息数：{len(agent.messages)}")


def test_custom_llm_config():
    """测试自定义 LLM 配置"""
    print("\n" + "=" * 60)
    print("测试 4: 自定义 LLM 配置")
    print("=" * 60)
    
    # 注意：这个测试需要有效的 API Key
    try:
        # 创建一个自定义配置（这里只是示例，不会真正调用）
        config = LLMConfig(
            provider="kimi",
            api_key=os.getenv("API_KEY"),  # 从环境变量读取
            model="kimi-k2.5"
        )
        
        agent = Agent(config=config)
        print(f"✓ 成功创建自定义配置的 Agent")
        print(f"  提供商：{agent.config.provider}")
        print(f"  模型：{agent.config.model}")
        
    except Exception as e:
        print(f"✗ 创建失败：{e}")


def test_mcp_tools():
    """测试 MCP 工具集成"""
    print("\n" + "=" * 60)
    print("测试 5: MCP 工具集成")
    print("=" * 60)
    
    try:
        from app_qt.plugin_manager import get_plugin_manager
        
        # 获取插件管理器
        plugin_manager = get_plugin_manager()
        
        # 检查是否有启用 MCP 的方法
        all_methods = plugin_manager.get_all_methods(include_extra_data=True)
        mcp_methods = [
            m for m in all_methods 
            if m.get("extra_data", {}).get("enable_mcp", False)
        ]
        
        print(f"已注册的方法总数：{len(all_methods)}")
        print(f"启用 MCP 的方法数：{len(mcp_methods)}")
        
        if mcp_methods:
            print("\nMCP 方法列表:")
            for method in mcp_methods:
                print(f"  - {method['name']}")
        
        # 创建带插件管理器的 Agent
        agent = Agent(plugin_manager=plugin_manager)
        
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("IPython LLM Bridge 功能测试")
    print("=" * 70)
    
    # 选择要运行的测试
    tests = {
        "1": test_basic_chat,
        "2": test_history_memory,
        "3": test_clear_history,
        "4": test_custom_llm_config,
        "5": test_mcp_tools
    }
    
    print("\n请选择要运行的测试：")
    print("1. 基本对话功能")
    print("2. 历史记忆功能")
    print("3. 清除历史功能")
    print("4. 自定义 LLM 配置")
    print("5. MCP 工具集成")
    print("0. 运行所有测试")
    
    choice = input("\n请输入选项 (0-5): ").strip()
    
    if choice == "0":
        # 运行所有测试
        test_basic_chat()
        test_history_memory()
        test_clear_history()
        test_custom_llm_config()
        test_mcp_tools()
    elif choice in tests:
        tests[choice]()
    else:
        print("无效的选项")
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
