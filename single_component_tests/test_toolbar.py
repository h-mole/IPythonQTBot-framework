"""
测试 IPython 控制台工具条功能
"""
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QPushButton
from app_qt.ipython_console_tab import IPythonConsoleTab


class TestWindow(QMainWindow):
    """测试窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IPython 控制台工具条测试")
        self.resize(1200, 800)
        
        # 创建标签页
        tabs = QTabWidget()
        self.setCentralWidget(tabs)
        
        # 添加 IPython 控制台标签
        console_tab = IPythonConsoleTab()
        tabs.addTab(console_tab, "IPython Console")
        
        # 添加一个测试按钮来模拟状态更新
        test_btn_widget = QWidget()
        test_layout = QVBoxLayout()
        test_btn_widget.setLayout(test_layout)
        
        btn_generating = QPushButton("模拟生成中状态")
        btn_generating.clicked.connect(lambda: console_tab.update_status_display(status="generating"))
        test_layout.addWidget(btn_generating)
        
        btn_finished = QPushButton("模拟完成状态")
        btn_finished.clicked.connect(lambda: console_tab.update_status_display(status="finished"))
        test_layout.addWidget(btn_finished)
        
        btn_error = QPushButton("模拟错误状态")
        btn_error.clicked.connect(lambda: console_tab.update_status_display(status="error"))
        test_layout.addWidget(btn_error)
        
        btn_idle = QPushButton("模拟空闲状态")
        btn_idle.clicked.connect(lambda: console_tab.update_status_display(status="idle"))
        test_layout.addWidget(btn_idle)
        
        btn_tokens = QPushButton("设置 Token 数量为 1500")
        btn_tokens.clicked.connect(lambda: console_tab.update_status_display(tokens=1500))
        test_layout.addWidget(btn_tokens)
        
        tabs.addTab(test_btn_widget, "测试控件")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
