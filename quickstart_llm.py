"""
IPython LLM Agent 快速启动脚本

使用方法：
1. 直接运行此脚本启动 IPython 控制台
2. 在控制台中使用 agent.ask() 或 %agent_ask 进行对话

示例：
    python quickstart_llm.py
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def main():
    """启动 IPython 控制台并加载 LLM Agent"""
    print("="*70)
    print("IPython LLM Agent 快速启动")
    print("="*70)
    
    # 检查依赖
    try:
        import openai
        print("✓ openai 库已安装")
    except ImportError:
        print("✗ 错误：未安装 openai 库")
        print("  请运行：pip install openai")
        return
    
    # 检查 API Key
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv("API_KEY"):
        print("⚠ 警告：未在 .env 文件中找到 API_KEY")
        print("  请配置 API_KEY 后重试")
        print("\n支持的提供商:")
        print("  - Kimi: API_KEY (环境变量)")
        print("  - OpenAI: OPENAI_API_KEY")
        print("  - 智谱 AI: ZHIPU_API_KEY")
        return
    else:
        print("✓ API Key 已配置")
    
    print("\n正在启动 IPython...")
    print("-"*70)
    
    # 启动 IPython
    try:
        from IPython import start_ipython
        
        # 设置启动横幅
        banner = """
╔═══════════════════════════════════════════════════════════╗
║         IPython LLM Agent - 流式对话框架                    ║
╠═══════════════════════════════════════════════════════════╣
║  快速开始:                                                 ║
║    agent.ask('你好')           # 提问                      ║
║    agent.clear()               # 清除历史                  ║
║    %agent_ask <问题>           # Magic 命令                ║
║    %agent_clear                # 清除历史                  ║
║                                                           ║
║  查看帮助:                                                 ║
║    help(agent)                 # 查看 agent 帮助            ║
║    print(agent.messages)       # 查看历史消息              ║
╚═══════════════════════════════════════════════════════════╝
"""
        
        # 预导入模块
        ipython_args = [
            '--TerminalInteractiveShell.banner1=' + banner.replace('\n', '\\n'),
        ]
        
        start_ipython(argv=ipython_args)
        
    except Exception as e:
        print(f"\n启动失败：{e}")
        print("\n请确保已安装 IPython:")
        print("  pip install ipython")
        
        # 如果 IPython 不可用，提供备选方案
        print("\n" + "="*70)
        print("备选方案：直接使用 Python 测试")
        print("="*70)
        
        from app_qt.ipython_llm_bridge import Agent
        
        agent = Agent()
        print("\nAgent 已创建，可以开始对话:")
        print("  >>> agent.ask('你好')")
        
        # 进入交互式循环
        while True:
            try:
                user_input = input("\n>>> ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ('quit', 'exit'):
                    break
                
                agent.ask(user_input)
                
            except KeyboardInterrupt:
                print("\n\n再见!")
                break
            except Exception as e:
                print(f"错误：{e}")


if __name__ == "__main__":
    main()
