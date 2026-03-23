"""
测试快速笔记插件重构后的功能
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from PySide6.QtWidgets import QApplication
from plugins.quick_notes.main import QuickNotesTab

def test_quick_notes():
    """测试快速笔记插件"""
    app = QApplication(sys.argv)
    
    # 创建笔记标签页
    notes_tab = QuickNotesTab()
    notes_tab.setWindowTitle("快速笔记测试")
    notes_tab.resize(1200, 800)
    notes_tab.show()
    
    print("=" * 60)
    print("快速笔记插件功能测试")
    print("=" * 60)
    print("\n测试内容：")
    print("1. 菜单栏功能：📝 笔记操作菜单")
    print("   - 📄 新建笔记 (Ctrl+N)")
    print("   - 📁 新建文件夹")
    print("   - ✨ 创建技能")
    print("   - 🔄 刷新 (F5)")
    print("\n2. 树结构上下文菜单（右键点击）")
    print("   - 📄 新建笔记")
    print("   - 📁 新建文件夹")
    print("   - ✨ 创建技能")
    print("   - ✏️ 重命名")
    print("   - 🗑️ 删除")
    print("   - 📂 在文件管理器中打开")
    print("\n3. 刷新事件触发")
    print("   - 保存文件时自动刷新")
    print("   - 创建技能时自动刷新")
    print("\n" + "=" * 60)
    print("请手动测试以上功能，确保一切正常工作")
    print("=" * 60)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_quick_notes()
