"""
测试 IPython 插件桥接的自动补全功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_qt.plugin_manager import get_plugin_manager
from app_qt.ipython_plugins_bridge import init_ipython_plugins_api


def test_autocomplete():
    """测试自动补全功能"""
    print("=" * 60)
    print("测试 IPython 插件桥接自动补全功能")
    print("=" * 60)
    
    # 获取插件管理器实例
    plugin_manager = get_plugin_manager()
    
    # 创建插件 API 对象
    plugins_api = init_ipython_plugins_api(plugin_manager)
    
    print("\n1. 测试 plugins.call 的自动补全")
    print("-" * 60)
    
    # 获取 plugins.call 的所有可用属性（应该是所有插件名称）
    call_dir = dir(plugins_api.call)
    print(f"plugins.call 可用的插件名称：{call_dir}")
    
    if call_dir:
        print(f"\n✓ 自动补全成功！共 {len(call_dir)} 个插件可补全")
        
        # 测试第一个插件的方法补全
        first_plugin = call_dir[0]
        print(f"\n2. 测试 plugins.call.{first_plugin} 的方法补全")
        print("-" * 60)
        
        # 获取该插件的所有方法
        plugin_wrapper = getattr(plugins_api.call, first_plugin)
        methods = dir(plugin_wrapper)
        print(f"plugins.call.{first_plugin} 可用的方法：{methods}")
        
        if methods:
            print(f"\n✓ 方法补全成功！共 {len(methods)} 个方法可补全")
        else:
            print(f"\n⚠ 插件 {first_plugin} 没有注册方法")
    else:
        print("\n✗ 没有可用的插件（可能插件未加载）")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    # 使用说明
    print("\n在 IPython 中的使用效果:")
    print("-" * 60)
    print(">>> plugins.call.<TAB>")
    print("    将显示所有已加载的插件名称:")
    for plugin_name in call_dir[:5]:  # 显示前 5 个
        print(f"      - {plugin_name}")
    if len(call_dir) > 5:
        print(f"      ... 还有 {len(call_dir) - 5} 个")
    
    print("\n>>> plugins.call.text_helper.<TAB>")
    print("    将显示该插件的所有方法:")
    if 'text_helper' in call_dir:
        text_helper_wrapper = getattr(plugins_api.call, 'text_helper')
        text_methods = dir(text_helper_wrapper)
        for method in text_methods[:5]:  # 显示前 5 个
            print(f"      - {method}")
    
    print("\n示例代码:")
    print("  >>> plugins.call.text_helper.get_text()")
    print("  >>> plugins.call.quick_notes.create_note('my_note')")
    print("=" * 60)


if __name__ == "__main__":
    test_autocomplete()
