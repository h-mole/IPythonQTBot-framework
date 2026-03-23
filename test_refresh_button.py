"""
测试笔记树刷新按钮
"""

import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

# 添加插件路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'plugins', 'quick_notes'))

from components.note_tree_widget import NoteTreeWidget


class TestWindow(QMainWindow):
    """测试窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("笔记树刷新按钮测试")
        self.setGeometry(100, 100, 400, 600)
        
        # 创建中心小部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建笔记树
        notes_dir = r"C:\Users\hzy\IPythonQTBot\plugin_data\quick_notes\skills"
        allowed_extensions = ['.md', '.txt']
        
        self.note_tree = NoteTreeWidget(notes_dir, allowed_extensions)
        self.note_tree.load_tree()
        layout.addWidget(self.note_tree)
        
        # 连接信号
        self.note_tree.refresh_requested.connect(self.on_refresh)
        self.note_tree.note_clicked.connect(self.on_note_clicked)
        
        print("提示：点击右上角的 🔄 按钮或按 F5 刷新笔记目录")
    
    def on_refresh(self):
        """刷新事件"""
        print(">>> 笔记目录已刷新")
        self.note_tree.load_tree()
    
    def on_note_clicked(self, file_path):
        """笔记点击事件"""
        print(f">>> 点击笔记：{file_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())
