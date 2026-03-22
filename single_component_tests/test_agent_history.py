"""
测试 Agent 历史对话保存和加载功能

使用方法:
1. 在 IPython 控制台中运行此脚本
2. 测试保存和加载功能
"""

from app_qt.ipython_llm_bridge import Agent, LLMConfig
from app_qt.plugin_manager import get_plugin_manager

def test_history_save_load():
    """测试历史对话的保存和加载"""
    
    # 获取插件管理器
    pm = get_plugin_manager()
    
    # 创建 Agent 实例 (需要传入 ipython_tab，这里简化测试)
    print("=" * 60)
    print("测试历史对话功能")
    print("=" * 60)
    
    # 示例 1: 手动创建配置并保存
    print("\n1. 创建测试对话...")
    config = LLMConfig(provider="kimi")
    
    # 注意：实际使用时需要通过 init_ipython_llm_agent_api 初始化
    # 这里只是演示 API
    
    print("\n2. 自动保存功能...")
    print("   每次调用 agent.ask() 时会自动保存对话")
    print("   文件保存在：MAIN_APP_DATA_DIR/llm_conversation_history/")
    print("   文件名格式：conversation_YYYYMMDD_HHMMSS.json")
    
    print("\n3. 列出最近的对话...")
    print("   agent.list_recent_conversations()  # 列出最近 10 个对话")
    print("   agent.list_recent_conversations(limit=5)  # 列出最近 5 个")
    
    print("\n4. 加载历史对话...")
    print("   agent.load_history()  # 自动加载最近的对话")
    print("   agent.load_history('conversation_20250322_143022.json')  # 加载指定文件")
    
    print("\n5. 手动保存...")
    print("   agent.save_history()  # 使用自动生成文件名")
    print("   agent.save_history('my_chat.json')  # 保存到指定文件")
    
    print("\n" + "=" * 60)
    print("JSON 文件格式:")
    print("=" * 60)
    print("""
{
    "messages": [...],                      // 对话历史消息列表
    "mcp_tools_enabled": [],                // 启用的 MCP 工具名称列表
    "mcp_tools_disabled": [],               // 禁用的 MCP 工具名称列表
    "config": {                             // LLM 配置 (可选)
        "provider": "kimi",
        "api_key": "...",
        "base_url": "...",
        "model": "..."
    },
    "conversation_start_time": "20250322_143022"  // 对话开始时间戳
}
    """)
    
    print("\n" + "=" * 60)
    print("使用示例:")
    print("=" * 60)
    print("""
# 在 IPython 控制台中:

# 1. 开始对话 (会自动保存)
agent.ask("你好，请帮我写一个 Python 函数")
# 输出：[Agent] 新对话已开始，时间：20250322_143022
# 自动保存到：~/myhelper/app_data/llm_conversation_history/conversation_20250322_143022.json

# 2. 继续对话 (继续自动保存)
agent.ask("能再优化一下这个函数吗？")

# 3. 查看最近的对话
agent.list_recent_conversations()
# 输出:
# [Agent] 找到 3 个历史对话文件:
#   1. conversation_20250322_143022.json (2025-03-22 14:30:22)
#   2. conversation_20250322_120000.json (2025-03-22 12:00:00)
#   3. conversation_20250321_180000.json (2025-03-21 18:00:00)

# 4. 加载最近的对话
agent.load_history()  # 自动加载最新的对话

# 5. 加载指定的历史对话
agent.load_history('conversation_20250322_120000.json')

# 6. 清除当前对话
agent.clear()

# 7. 手动保存（使用自定义文件名）
agent.save_history('important_discussion.json')
    """)

if __name__ == "__main__":
    test_history_save_load()
