"""
Agent 历史对话功能演示脚本

运行此脚本可以查看和测试历史对话功能
"""

from pathlib import Path
from app_qt.configs import MAIN_APP_DATA_DIR
import json
import os


def demo_history_directory():
    """演示查看历史对话目录"""
    print("=" * 60)
    print("📁 Agent 历史对话目录")
    print("=" * 60)
    
    history_dir = MAIN_APP_DATA_DIR / "llm_conversation_history"
    print(f"\n历史对话存储位置：\n{history_dir}")
    print(f"\n目录是否存在：{history_dir.exists()}")
    
    if history_dir.exists():
        # 列出所有对话文件
        files = list(history_dir.glob("conversation_*.json"))
        print(f"\n找到 {len(files)} 个历史对话文件:")
        
        if files:
            # 按修改时间排序
            files_with_mtime = [(f, f.stat().st_mtime) for f in files]
            files_with_mtime.sort(key=lambda x: x[1], reverse=True)
            
            for i, (file_path, mtime) in enumerate(files_with_mtime[:10], 1):
                from datetime import datetime
                time_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                print(f"  {i}. {file_path.name} ({time_str})")
        else:
            print("  (暂无历史文件)")
    
    print()


def demo_json_structure(file_path=None):
    """演示 JSON 文件结构"""
    print("=" * 60)
    print("📄 JSON 文件结构示例")
    print("=" * 60)
    
    if file_path is None:
        # 查找最近的文件
        history_dir = MAIN_APP_DATA_DIR / "llm_conversation_history"
        if history_dir.exists():
            files = list(history_dir.glob("conversation_*.json"))
            if files:
                files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                file_path = files[0]
    
    if file_path and os.path.exists(file_path):
        print(f"\n文件：{file_path}\n")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("文件内容概览:")
        print(f"  - 消息数量：{len(data.get('messages', []))}")
        print(f"  - 启用工具：{len(data.get('mcp_tools_enabled', []))} 个")
        print(f"  - 禁用工具：{len(data.get('mcp_tools_disabled', []))} 个")
        print(f"  - 对话开始时间：{data.get('conversation_start_time', 'N/A')}")
        
        if 'config' in data:
            config = data['config']
            print(f"  - LLM 提供商：{config.get('provider', 'N/A')}")
            print(f"  - 模型：{config.get('model', 'N/A')}")
        
        print("\n消息预览:")
        messages = data.get('messages', [])
        for i, msg in enumerate(messages[-3:], max(0, len(messages)-3)):  # 只显示最后 3 条
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:100]
            print(f"  [{i+1}] {role}: {content}...")
    else:
        print("\n没有找到历史对话文件")
        print("提示：先使用 agent.ask() 进行对话，会自动保存历史")
    
    print()


def demo_api_usage():
    """演示 API 使用方法"""
    print("=" * 60)
    print("🚀 API 使用示例")
    print("=" * 60)
    
    print("""
# 1. 开始对话（自动保存）
agent.ask("你好，请帮我写一个 Python 函数")
# → 自动创建 conversation_YYYYMMDD_HHMMSS.json

# 2. 继续对话（自动更新同一文件）
agent.ask("能优化一下这个函数吗？")

# 3. 查看所有历史对话
agent.list_recent_conversations()
# 输出:
# [Agent] 找到 N 个历史对话文件:
#   1. conversation_xxx.json (时间)
#   2. conversation_xxx.json (时间)

# 4. 加载最近的对话
agent.load_history()  # 自动选择最新的文件

# 5. 加载指定的对话
agent.load_history('conversation_20250322_143022.json')

# 6. 清除当前对话并开始新的
agent.clear()
agent.ask("新话题...")  # 会创建新的对话文件

# 7. 手动保存（可选）
agent.save_history()  # 保存到当前文件名
agent.save_history('important.json')  # 自定义文件名
    """)


def demo_use_cases():
    """演示典型使用场景"""
    print("=" * 60)
    print("💡 典型使用场景")
    print("=" * 60)
    
    print("""
场景 1: 日常开发对话
─────────────────────
1. 早上开始工作：agent.ask("今天要做个新项目")
   → 自动保存为 conversation_morning.json
    
2. 下午继续：agent.ask("早上的项目，我想加个功能")
   → 加载早上的对话继续
    
3. 下班前清理：agent.clear()
   → 明天开始新的对话

场景 2: 多项目管理
─────────────────────
1. 项目 A: agent.ask("A 项目的数据库设计")
   → conversation_projectA.json
    
2. 切换到 B: agent.clear()
   agent.ask("B 项目的 API 架构")
   → conversation_projectB.json
    
3. 切换回 A: agent.load_history('conversation_projectA.json')

场景 3: 学习和研究
─────────────────────
1. 学习新技术：agent.ask("什么是 Docker?")
   → 自动保存学习内容
    
2. 复习：agent.load_history()
   → 加载之前的学习笔记
    
3. 整理：查看历史记录，导出重要内容
    """)


def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "Agent 历史对话功能演示" + " " * 15 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    # 演示 1: 查看目录
    demo_history_directory()
    
    # 演示 2: JSON 结构
    demo_json_structure()
    
    # 演示 3: API 使用
    demo_api_usage()
    
    # 演示 4: 使用场景
    demo_use_cases()
    
    print("=" * 60)
    print("📚 更多信息请查看:")
    print("   - docs/agent_history_feature.md (详细文档)")
    print("   - docs/agent_history_quickref.md (快速参考)")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
