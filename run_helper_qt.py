"""
快捷助手启动脚本 - PySide6 版本
"""

import sys
import os

# 确保项目根目录在路径中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from app_qt.logger import system_logger
from app_qt import main

if __name__ == "__main__":
    main()
