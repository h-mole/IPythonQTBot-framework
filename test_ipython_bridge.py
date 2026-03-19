"""
测试 IPython 插件桥接功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_qt.plugin_manager import get_plugin_manager
from app_qt.ipython_plugins_bridge import init_ipython_plugins_api


def test_plugins_api():
    """测试插件 API 功能"""
    print("=" * 60)
    print("测试 IPython 插件桥接功能")
    print("=" * 60)
    
    # 获取插件管理器实例
    plugin_manager = get_plugin_manager()
    
    # 创建插件 API 对象
    plugins_api = init_ipython_plugins_api(plugin_manager)
    
    print("\n1. 测试 plugins.list()")
    print("-" * 60)
    plugins_dict = plugins_api.list()
    
    print("\n2. 测试 plugins.methods()")
    print("-" * 60)
    all_methods = plugins_api.methods()
    
    # 测试调用插件方法（如果有的话）
    if plugins_dict:
        print("\n3. 测试插件方法调用")
        print("-" * 60)
        
        # 示例：如果有 text_helper 插件
        if 'text_helper' in plugins_dict:
            print("\n尝试调用 text_helper.get_text():")
            try:
                # 注意：这里需要在 Qt 应用环境中才能正确执行
                # 实际使用会在 IPython 中自动处理
                result = plugins_api.call.text_helper.get_text()  # type: ignore
                print(f"get_text() 返回：{result}")
            except Exception as e:
                print(f"调用失败（正常，因为不在 Qt 环境中）：{e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_plugins_api()
