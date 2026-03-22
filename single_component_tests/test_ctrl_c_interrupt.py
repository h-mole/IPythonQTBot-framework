"""
测试 Ctrl+C 中断功能

运行此脚本来测试 IPython 控制台标签页的 Ctrl+C 中断功能。

使用方法：
1. 运行脚本
2. 在 IPython 控制台中输入 agent.ask("一个问题")
3. 在生成过程中按下 Ctrl+C
4. 验证生成是否被停止
"""

import sys
from PySide6.QtWidgets import QApplication
from app_qt.ipython_console_tab import IPythonConsoleTab

def test_ctrl_c_interrupt():
    """测试 Ctrl+C 中断功能"""
    app = QApplication(sys.argv)
    
    # 创建 IPython 控制台标签页
    console_tab = IPythonConsoleTab()
    console_tab.show()
    
    print("=" * 60)
    print("Ctrl+C 中断功能测试")
    print("=" * 60)
    print("\n测试步骤:")
    print("1. 在 IPython 控制台中输入：agent.ask('请写一篇长文章')")
    print("2. 在生成过程中按下 Ctrl+C")
    print("3. 观察控制台输出和状态变化")
    print("=" * 60)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_ctrl_c_interrupt()
