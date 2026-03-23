"""
测试笔记树的无限层级功能
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from PySide6.QtWidgets import QApplication
from plugins.quick_notes.main import QuickNotesTab


def test_tree_levels():
    """测试树的多层结构"""
    print("=" * 60)
    print("测试笔记树无限层级功能")
    print("=" * 60)
    
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = QuickNotesTab()
    window.setWindowTitle("快速笔记 - 无限层级测试")
    window.resize(1200, 800)
    window.show()
    
    # 创建测试目录结构
    print("\n创建测试目录结构...")
    
    test_structure = [
        "level1/level2/level3/level4/test.md",
        "a/b/c/d/e/deep_note.md",
        "folder1/subfolder/file.md",
        "folder1/another_subfolder/another_file.md",
    ]
    
    for rel_path in test_structure:
        full_path = os.path.join(window.notes_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        if not os.path.exists(full_path):
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(f"# Test file at {rel_path}\n\nThis is a test file to verify tree levels.")
    
    print("✓ 测试目录创建完成")
    print(f"\n测试文件位置:")
    for rel_path in test_structure:
        print(f"  - {rel_path}")
    
    # 刷新树
    window.load_note_tree()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n请检查:")
    print("1. 树状结构是否正确显示多层文件夹")
    print("2. 展开所有节点，确认层级关系正确")
    print("3. 点击不同层级的文件，确认可以正常打开")
    print("4. 尝试在深层文件夹中创建新笔记")
    print("\n提示：可以在左侧树中右键文件夹来创建子文件夹，测试更多层级")
    print("\n")
    
    sys.exit(app.exec())


if __name__ == '__main__':
    test_tree_levels()
