"""
测试快速笔记插件的组件化重构和技能创建功能
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PySide6.QtWidgets import QApplication
from plugins.quick_notes.main import QuickNotesTab
from app_qt.plugin_manager import PluginManager


def test_quick_notes_components():
    """测试快速笔记组件"""
    print("=" * 60)
    print("测试快速笔记插件组件化重构")
    print("=" * 60)
    
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = QuickNotesTab()
    window.setWindowTitle("快速笔记 - 组件化测试")
    window.resize(1200, 800)
    window.show()
    
    print("\n✓ 快速笔记界面加载成功")
    print(f"✓ 笔记目录：{window.notes_dir}")
    print(f"✓ Skills 目录：{window.skills_dir}")
    
    # 测试组件是否存在
    assert hasattr(window, 'note_tree'), "笔记树组件未找到"
    assert hasattr(window, 'editor'), "文本编辑器组件未找到"
    assert hasattr(window, 'editor_toolbar'), "编辑器工具栏未找到"
    assert hasattr(window, 'find_panel'), "查找替换面板未找到"
    assert hasattr(window, 'create_skill_btn'), "创建技能按钮未找到"
    
    print("\n✓ 所有组件加载成功:")
    print("  - NoteTreeWidget (笔记树)")
    print("  - TextEditorWidget (文本编辑器)")
    print("  - EditorToolbar (编辑器工具栏)")
    print("  - FindReplacePanel (查找替换面板)")
    print("  - CreateSkillDialog (创建技能对话框)")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n提示:")
    print("1. 点击 '✨ 创建技能' 按钮测试技能创建功能")
    print("2. 技能将保存在 skills 文件夹下")
    print("3. 技能格式符合 agentskills-core 规范")
    print("\n")
    
    sys.exit(app.exec())


if __name__ == '__main__':
    test_quick_notes_components()
