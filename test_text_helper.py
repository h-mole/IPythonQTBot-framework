"""
测试 text_helper 插件的自定义菜单注册功能
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from PySide6.QtWidgets import QApplication
from app_qt.plugin_manager import PluginManager


def test_text_helper_plugin():
    """测试 text_helper 插件功能"""

    print("=" * 60)
    print("Text Helper 插件功能测试")
    print("=" * 60)

    # 创建 QApplication（必需）
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()

    # 获取插件管理器实例
    plugin_manager = PluginManager.get_instance()

    # 模拟主窗口环境（简化版）
    class MockNotebook:
        def addTab(self, *args):
            pass

        def insertTab(self, *args):
            pass

    class MockMenuBar:
        def addMenu(self, *args):
            pass

    # 设置主窗口引用并加载插件
    plugin_manager.set_main_window(None, MockNotebook(), MockMenuBar())
    plugin_manager.load_plugins()

    # 测试 1: 检查插件是否加载
    print("\n[测试 1] 检查已加载的插件...")
    if plugin_manager.is_plugin_loaded("text_helper"):
        print("✓ text_helper 插件已成功加载")
    else:
        print("✗ text_helper 插件未加载")
        return False

    # 测试 2: 获取并调用文本处理方法
    print("\n[测试 2] 测试文本处理方法...")

    remove_newlines = plugin_manager.get_method("text_helper.remove_newlines")
    if remove_newlines:
        print("✓ 成功获取 text_helper.remove_newlines 方法")

        # 测试去除换行符
        test_text = "第一行\n第二行\n第三行"
        result = remove_newlines(test_text)
        expected = "第一行 第二行 第三行"
        if result == expected:
            print(f"✓ remove_newlines 方法工作正常：'{test_text}' -> '{result}'")
        else:
            print(f"✗ remove_newlines 方法结果不正确")
            print(f"  预期：{expected}")
            print(f"  实际：{result}")
            return False
    else:
        print("✗ 无法获取 text_helper.remove_newlines 方法")
        return False

    # 测试 3: 测试其他文本处理方法
    print("\n[测试 3] 测试其他文本处理方法...")

    add_double_newlines = plugin_manager.get_method("text_helper.add_double_newlines")
    if add_double_newlines:
        test_text = "第一行\n第二行"
        result = add_double_newlines(test_text)
        expected = "第一行\n\n第二行"
        if result == expected:
            print(f"✓ add_double_newlines 方法工作正常")
        else:
            print(f"✗ add_double_newlines 方法结果不正确")
            return False

    remove_illegal = plugin_manager.get_method("text_helper.remove_illegal_chars")
    if remove_illegal:
        print("✓ remove_illegal_chars 方法可用")

    remove_filename = plugin_manager.get_method(
        "text_helper.remove_filename_illegal_chars"
    )
    if remove_filename:
        print("✓ remove_filename_illegal_chars 方法可用")

    # 测试 4: 测试注册自定义菜单项
    print("\n[测试 4] 测试注册自定义文本处理菜单...")

    register_action = plugin_manager.get_method("text_helper.register_text_action")
    if register_action:
        print("✓ 成功获取 register_text_action 方法")

        # 定义自定义处理函数
        def custom_uppercase(text):
            """将文本转换为大写"""
            return text.upper()

        # 注册自定义菜单项
        success = register_action(
            name="转换为大写", callback=custom_uppercase, shortcut="Ctrl+Alt+U"
        )

        if success:
            print("✓ 成功注册自定义菜单项 '转换为大写'")
        else:
            print("✗ 注册自定义菜单项失败")
            return False

        # 再注册一个测试
        def custom_reverse(text):
            """反转文本"""
            return text[::-1]

        success = register_action(name="反转文本", callback=custom_reverse)

        if success:
            print("✓ 成功注册自定义菜单项 '反转文本'")
        else:
            print("✗ 注册第二个菜单项失败")
            return False

    else:
        print("✗ 无法获取 register_text_action 方法")
        return False

    # 测试 5: 列出所有已注册的方法
    print("\n[测试 5] 查看所有已注册的方法...")
    all_methods = plugin_manager.get_all_methods()
    if all_methods:
        print(f"✓ 当前已注册 {len(all_methods)} 个方法:")
        for method in all_methods:
            print(f"  - {method}")
    else:
        print("⚠ 没有已注册的方法")

    print("\n" + "=" * 60)
    print("所有测试通过！✓")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_text_helper_plugin()
    sys.exit(0 if success else 1)
