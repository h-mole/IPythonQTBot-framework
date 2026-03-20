"""
IPython LLM Agent 演示脚本

在 IPython 控制台中运行此脚本查看演示
"""

def demo_basic_usage():
    """演示基本用法"""
    print("\n" + "="*70)
    print("演示 1: 基本对话")
    print("="*70)
    
    print("""
# 最简单的使用方式
agent.ask("你好，请介绍一下自己")

# 查看历史对话
print(f"当前对话数：{len(agent.messages)}")

# 清除历史
agent.clear()
    """)


def demo_context_memory():
    """演示上下文记忆"""
    print("\n" + "="*70)
    print("演示 2: 上下文记忆")
    print("="*70)
    
    print("""
# 第一轮对话
agent.ask("我喜欢吃苹果和香蕉")

# 第二轮（会记住第一轮的内容）
agent.ask("我最喜欢的水果是什么？")
# Agent 会回答：苹果和香蕉

# 第三轮（继续基于上下文）
agent.ask("那如果我想要更健康的饮食，应该怎么搭配？")
# Agent 会基于之前的水果偏好给出建议
    """)


def demo_magic_commands():
    """演示 Magic 命令"""
    print("\n" + "="*70)
    print("演示 3: Magic 命令")
    print("="*70)
    
    print("""
# 使用 Magic 命令提问（更方便）
%agent_ask 什么是 Python 的列表推导式？

# 继续提问
%agent_ask 能给我三个实际应用的例子吗？

# 清除历史
%agent_clear

# 开始新话题
%agent_ask 现在我们聊聊机器学习
    """)


def demo_custom_config():
    """演示自定义配置"""
    print("\n" + "="*70)
    print("演示 4: 自定义 LLM 配置")
    print("="*70)
    
    print("""
from app_qt.ipython_llm_bridge import Agent, LLMConfig

# 使用 Kimi
config_kimi = LLMConfig(provider="kimi", model="kimi-k2.5")
agent_kimi = Agent(config=config_kimi)

# 使用 OpenAI（需要 OPENAI_API_KEY 环境变量）
# config_openai = LLMConfig(provider="openai", model="gpt-3.5-turbo")
# agent_openai = Agent(config=config_openai)

# 使用智谱 AI（需要 ZHIPU_API_KEY 环境变量）
# config_zhipu = LLMConfig(provider="zhipu", model="glm-4")
# agent_zhipu = Agent(config=config_zhipu)
    """)


def demo_system_prompt():
    """演示系统提示词"""
    print("\n" + "="*70)
    print("演示 4: 设置系统提示词")
    print("="*70)
    
    print("""
# 设置专业角色
agent.set_system_prompt("你是一个资深的 Python 架构师，专注于代码质量和最佳实践")

# 然后提问
agent.ask("如何设计一个可扩展的日志系统？")

# 切换到另一个角色
agent.clear()
agent.set_system_prompt("你是一个友好的编程导师，擅长用简单易懂的方式解释概念")
agent.ask("什么是闭包？")
    """)


def demo_mcp_integration():
    """演示 MCP 工具集成"""
    print("\n" + "="*70)
    print("演示 5: MCP 工具集成")
    print("="*70)
    
    print("""
# 如果插件中有方法配置了 enable_mcp=True
# 例如：text_helper.remove_newlines_api

# Agent 会自动调用这些工具
agent.ask("请帮我处理这段文本，去除所有的换行符")

# Agent 会：
# 1. 理解你的需求
# 2. 自动调用 text_helper.remove_newlines_api 方法
# 3. 返回处理结果
    """)


def show_quick_reference():
    """显示快速参考"""
    print("\n" + "="*70)
    print("快速参考")
    print("="*70)
    
    print("""
常用方法:
  - agent.ask("问题")          # 提问
  - agent.clear()              # 清除历史
  - agent.set_system_prompt("提示词")  # 设置系统提示
  - len(agent.messages)        # 查看历史消息数
  
Magic 命令:
  - %agent_ask <问题>          # 提问
  - %agent_clear               # 清除历史

查看状态:
  - print(agent.messages)      # 查看所有历史消息
  - print(agent.config)        # 查看当前配置
    """)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("IPython LLM Agent 演示")
    print("="*70)
    
    print("""
本演示展示了如何使用 IPython LLM Agent 进行流式对话。

选择要运行的演示:
1. 基本对话
2. 上下文记忆
3. Magic 命令
4. 自定义配置
5. 系统提示词
6. MCP 工具集成
0. 显示所有演示
    """)
    
    choice = input("请输入选项 (0-6): ").strip()
    
    demos = {
        "1": demo_basic_usage,
        "2": demo_context_memory,
        "3": demo_magic_commands,
        "4": demo_custom_config,
        "5": demo_system_prompt,
        "6": demo_mcp_integration,
    }
    
    if choice == "0":
        demo_basic_usage()
        demo_context_memory()
        demo_magic_commands()
        demo_custom_config()
        demo_system_prompt()
        demo_mcp_integration()
        show_quick_reference()
    elif choice in demos:
        demos[choice]()
    else:
        print("无效的选项")
        show_quick_reference()
    
    print("\n" + "="*70)
    print("提示：在 IPython 控制台中直接输入 agent.ask('你的问题') 开始使用！")
    print("="*70 + "\n")
