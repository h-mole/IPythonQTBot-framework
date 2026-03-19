"""
快捷助手 - PySide6 版本
应用入口文件
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app_qt.main_window import QuickAssistant


def main():
    """主函数"""
    # 启用高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("快捷助手")
    app.setOrganizationName("MyHelper")
    app.setApplicationVersion("1.0.0")
    
    # 设置样式
    app.setStyle("Fusion")
    
    window = QuickAssistant()
    window.show()
    
    # 初始隐藏到托盘
    window.hide()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
