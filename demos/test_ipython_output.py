"""
在真实 IPython 环境中测试 LLM Agent 输出

使用方法：
1. 运行主程序：python run_helper_qt.py
2. 切换到 IPython 控制台标签页
3. 输入以下命令测试：
   
   agent.ask("你好，请简单介绍一下自己")
   
4. 观察是否有流式输出显示在 IPython 控制台中
"""

def test_in_ipython():
    """在 IPython 中测试"""
    print("="*70)
    print("IPython LLM Agent 测试")
    print("="*70)
    
    # 检查 agent 是否存在
    try:
        agent
    except NameError:
        print("错误：agent 对象不存在！")
        print("请确保 IPython 控制台已正确初始化 LLM Agent")
        return
    
    print("✓ agent 对象已存在")
    print(f"✓ 当前配置：{agent.config.provider} / {agent.config.model}")
    print()
    
    # 测试基本对话
    print("-"*70)
    print("开始测试对话...")
    print("-"*70)
    
    agent.ask("你好，请用一句话介绍你自己")
    
    print("\n\n如果看到上面的流式输出，说明功能正常！✅")
    print("如果没有看到输出，说明需要调试输出系统。❌")


if __name__ == "__main__":
    test_in_ipython()
