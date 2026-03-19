"""
测试插件系统功能
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app_qt.plugin_manager import PluginManager
from PySide6.QtWidgets import QApplication


def test_plugin_system():
    """测试插件系统的各项功能"""

    # 创建 QApplication（必需）
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()

    print("=" * 60)
    print("插件系统功能测试")
    print("=" * 60)

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
    if plugin_manager.is_plugin_loaded("quick_notes"):
        print("✓ quick_notes 插件已成功加载")
    else:
        print("✗ quick_notes 插件未加载")
        return False

    # 测试 2: 获取并调用插件方法
    print("\n[测试 2] 测试插件方法调用...")

    # 获取 create_note 方法
    create_note = plugin_manager.get_method("quick_notes.create_note")
    if create_note:
        print("✓ 成功获取 quick_notes.create_note 方法")
    else:
        print("✗ 无法获取 quick_notes.create_note 方法")
        return False

    # 获取 load_note 方法
    load_note = plugin_manager.get_method("quick_notes.load_note")
    if load_note:
        print("✓ 成功获取 quick_notes.load_note 方法")
    else:
        print("✗ 无法获取 quick_notes.load_note 方法")
        return False

    # 获取 save_note 方法
    save_note = plugin_manager.get_method("quick_notes.save_note")
    if save_note:
        print("✓ 成功获取 quick_notes.save_note 方法")
    else:
        print("✗ 无法获取 quick_notes.save_note 方法")
        return False

    # 测试 3: 实际调用方法（创建测试笔记）
    print("\n[测试 3] 实际调用插件方法...")

    try:
        # 创建测试笔记
        note_path = create_note(name="测试笔记", folder="TestFolder")
        print(f"✓ 成功创建笔记：{note_path}")

        # 保存内容到笔记
        test_content = "这是测试笔记的内容\n第二行"
        success = save_note(path=note_path, content=test_content)
        if success:
            print(f"✓ 成功保存笔记内容")
        else:
            print(f"✗ 保存笔记失败")
            return False

        # 读取笔记内容
        content = load_note(path=note_path)
        if content == test_content:
            print(f"✓ 成功读取笔记内容，内容正确")
        else:
            print(f"✗ 读取内容与预期不符")
            print(f"  预期：{test_content}")
            print(f"  实际：{content}")
            return False

    except Exception as e:
        print(f"✗ 调用方法时出错：{e}")
        import traceback

        traceback.print_exc()
        return False

    # 测试 4: 列出所有已注册的方法
    print("\n[测试 4] 查看所有已注册的方法...")
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
    success = test_plugin_system()
    sys.exit(0 if success else 1)
