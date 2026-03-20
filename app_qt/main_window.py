"""
快捷助手 - PySide6 版本
迁移自 helperscript.py
"""

import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QListWidget,
    QGroupBox,
    QFrame,
    QSplitter,
    QSystemTrayIcon,
    QMenu,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtCore import Signal

# 导入标签页模块
from app_qt.ipython_console_tab import IPythonConsoleTab

# 任务管理器已迁移到插件


class QuickAssistant(QMainWindow):
    """快捷助手主窗口"""

    def __init__(self):
        super().__init__()

        # 窗口设置
        self.setWindowTitle("快捷助手")
        self.setGeometry(100, 100, 900, 600)

        # 剪贴板历史记录
        self.clipboard_history = []
        self.max_clipboard_history = 50

        # 先加载插件（在主线程中）
        self._load_plugins_before_ui()

        # 创建界面组件
        self.create_widgets()

        # 系统托盘
        self.tray_icon = None
        self.create_tray()

    def _load_plugins_before_ui(self):
        """在创建 UI 之前加载插件（确保在主线程中）"""
        try:
            from app_qt.plugin_manager import get_plugin_manager

            # 获取插件管理器实例
            plugin_manager = get_plugin_manager()

            # 设置主窗口引用（此时 notebook 还未创建）
            plugin_manager.set_main_window(self, None, None)

            # 加载所有插件（在主线程中）
            plugin_manager.load_plugins()

            print("[MainWindow] 插件预加载完成")

        except Exception as e:
            print(f"[MainWindow] 插件预加载失败：{e}")
            import traceback

            traceback.print_exc()

    def create_widgets(self):
        """构建主界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # 顶部标题
        header = QLabel("🛠️ 快捷助手")
        header.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        # 创建标签页控件
        self.notebook = QTabWidget()
        main_layout.addWidget(self.notebook)

        # 更新插件管理器的 notebook 引用（此时已创建）
        from app_qt.plugin_manager import get_plugin_manager

        plugin_manager = get_plugin_manager()
        plugin_manager.set_main_window(self, self.notebook, None)

        # 第四个标签页：IPython 控制台
        self.ipython_console = IPythonConsoleTab()
        self.notebook.addTab(self.ipython_console, "🐍 IPython")

        # 启动剪贴板监控
        self.clipboard_timer = QTimer()
        self.clipboard_timer.timeout.connect(self.check_clipboard)
        self.clipboard_timer.start(1000)  # 每 1 秒检查一次
        self.last_clipboard = ""

    def on_clipboard_update(self, text):
        """剪贴板更新回调"""
        pass

    def check_clipboard(self):
        """检查剪贴板变化"""
        try:
            import pyperclip

            current = pyperclip.paste()
            if current and current != self.last_clipboard:
                self.last_clipboard = current
                # 添加到文本处理标签页的历史记录
                self.text_helper.add_to_clipboard_history(current)
        except:
            pass

    def create_tray(self):
        """创建系统托盘图标"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        # 创建图标
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor(240, 240, 240))
        painter = QPainter(pixmap)
        painter.setBrush(QColor(30, 144, 255))
        painter.drawRect(10, 10, 44, 44)
        painter.setBrush(QColor(240, 240, 240))
        painter.drawRect(15, 15, 34, 34)
        painter.end()

        icon = QIcon(pixmap)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("快捷助手")

        # 创建托盘菜单
        tray_menu = QMenu()

        show_action = QAction("打开主界面", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        quit_action = QAction("退出程序", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.show()

    def tray_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window()

    def show_window(self):
        """显示主窗口"""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def closeEvent(self, event):
        """关闭窗口事件"""
        # 隐藏而不是退出
        if self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

    def quit_app(self):
        """完全退出程序"""
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()

window = None  # 声明全局变量
def main():
    """主函数"""
    global window
    app = QApplication(sys.argv)

    # 设置应用信息
    app.setApplicationName("快捷助手")
    app.setOrganizationName("MyHelper")

    window = QuickAssistant()
    window.show()

    # 初始隐藏到托盘
    window.hide()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
