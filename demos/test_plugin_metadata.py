"""
测试插件管理器的方法元数据缓存功能
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from app_qt.plugin_manager import PluginManager

def test_metadata_cache():
    """测试方法元数据缓存功能"""
    # 创建 QApplication（需要用于加载包含 UI 组件的插件）
    app = QApplication(sys.argv)
    
    print("=" * 60)
    print("测试插件管理器方法元数据缓存")
    print("=" * 60)
    
    # 获取插件管理器实例
    plugin_manager = PluginManager.get_instance()
    
    # 加载插件
    plugin_manager.load_plugins()
    
    print("\n1. 测试 get_all_methods(include_extra_data=True)")
    all_methods = plugin_manager.get_all_methods(include_extra_data=True)
    
    for method in all_methods:
        method_name = method['name']
        extra_data = method.get('extra_data', {})
        
        print(f"\n  方法：{method_name}")
        if extra_data:
            print(f"    extra_data: {extra_data}")
            if extra_data.get('enable_mcp'):
                print(f"    ✓ 启用了 MCP")
        else:
            print(f"    (无 extra_data)")
    
    # 特别检查 daily_tasks.get_tasks 的 enable_mcp
    print("\n\n2. 特别检查 daily_tasks.get_tasks 方法")
    get_tasks_method = None
    for method in all_methods:
        if method['name'] == 'daily_tasks.get_tasks':
            get_tasks_method = method
            break
    
    if get_tasks_method:
        extra_data = get_tasks_method.get('extra_data', {})
        print(f"  方法信息：{get_tasks_method}")
        print(f"  enable_mcp: {extra_data.get('enable_mcp', False)}")
        
        if extra_data.get('enable_mcp'):
            print("  ✓ 正确读取到 enable_mcp=True")
        else:
            print("  ✗ enable_mcp 未正确读取")
    else:
        print("  ✗ 未找到 daily_tasks.get_tasks 方法")
    
    # 测试 get_method_extra_data
    print("\n\n3. 测试 get_method_extra_data")
    extra = plugin_manager.get_method_extra_data("daily_tasks.get_tasks")
    print(f"  daily_tasks.get_tasks 的 extra_data: {extra}")
    print(f"  enable_mcp: {extra.get('enable_mcp', False) if extra else False}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_metadata_cache()
