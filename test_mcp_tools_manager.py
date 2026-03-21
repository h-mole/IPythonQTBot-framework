"""
测试 MCP 工具管理功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_qt.plugin_manager import get_plugin_manager
from app_qt.ipython_console_tab import IPythonConsoleTab
from PySide6.QtWidgets import QApplication

def test_mcp_tools_manager():
    """测试 MCP 工具管理器"""
    print("=" * 60)
    print("测试 MCP 工具管理功能")
    print("=" * 60)
    
    # 创建 QApplication（需要用于 Qt 组件）
    app = QApplication.instance() or QApplication(sys.argv)
    
    # 获取插件管理器
    pm = get_plugin_manager()
    
    # 加载插件
    pm.load_plugins()
    
    # 获取所有 MCP 工具
    all_methods = pm.get_all_methods(include_extra_data=True)
    mcp_tools = [m for m in all_methods if m.get('extra_data', {}).get('enable_mcp', False)]
    
    print(f"\n找到 {len(mcp_tools)} 个 MCP 工具:")
    for tool in mcp_tools:
        print(f"  - {tool['name']}")
    
    # 按命名空间分组（支持 mcp_bridge 的特殊格式）
    namespace_groups = {}
    for tool in mcp_tools:
        parts = tool['name'].split('.', 1)
        if len(parts) == 2:
            namespace = parts[0]
            method_name = parts[1]
            
            # 特殊处理 mcp_bridge 的格式：mcp_bridge.mcd-mcp__xxxx
            # 需要按照双下划线前面的部分作为子分组
            if namespace == 'mcp_bridge' and '__' in method_name:
                sub_group = method_name.split('__')[0]  # 例如：mcd-mcp
                group_key = f"{namespace}.{sub_group}"
            else:
                group_key = namespace
            
            if group_key not in namespace_groups:
                namespace_groups[group_key] = []
            namespace_groups[group_key].append(tool)
    
    print(f"\n按分组显示:")
    for group_key, tools in sorted(namespace_groups.items()):
        print(f"  {group_key}: {len(tools)} 个工具")
    
    # 创建 IPython 控制台标签页
    print("\n创建 IPython 控制台...")
    console_tab = IPythonConsoleTab()
    
    # 等待内核初始化完成
    print("等待内核初始化...")
    import time
    time.sleep(3)  # 给内核初始化一些时间
    
    # 测试获取 MCP 工具状态
    print("\n测试 get_mcp_tools_status 方法:")
    status = console_tab.get_mcp_tools_status()
    print(f"  启用：{len(status['enabled'])} 个")
    print(f"  禁用：{len(status['disabled'])} 个")
    print(f"  总计：{status['total']} 个")
    
    # 显示对话框（可选）
    # print("\n打开 MCP 工具管理对话框...")
    # console_tab.show_mcp_tools_manager()
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

if __name__ == "__main__":
    test_mcp_tools_manager()
