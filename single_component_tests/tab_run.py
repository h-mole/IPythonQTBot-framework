"""
快速笔记功能测试脚本
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Qt

# 导入快速笔记模块
from app_qt.quicknotes_tab import QuickNotesTab


class TestWindow(QMainWindow):
    """测试窗口"""

    def __init__(self):
        super().__init__()

        # 窗口设置
        self.setWindowTitle("快速笔记功能测试")
        self.setGeometry(100, 100, 1200, 800)

        # 创建快速笔记标签页
        self.notes_tab = QuickNotesTab()
        self.setCentralWidget(self.notes_tab)


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用信息
    app.setApplicationName("快速笔记测试")
    app.setOrganizationName("MyHelper")

    window = TestWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
