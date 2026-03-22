"""
测试设置面板样式修复
"""

import sys
sys.path.append(r"C:\Users\hzy\Programs\myhelper")

from PySide6.QtWidgets import QApplication
from app_qt.configs import settings
from app_qt.widgets.settings_panel import SettingsDialog

# 创建应用
app = QApplication([])

print("=" * 60)
print("测试设置面板样式修复")
print("=" * 60)

# 创建设置对话框
dialog = SettingsDialog(settings)

print("\n✅ 设置对话框已创建")
print(f"   - 窗口标题：{dialog.windowTitle()}")
print(f"   - 最小尺寸：{dialog.minimumWidth()}x{dialog.minimumHeight()}")
print(f"   - 当前尺寸：{dialog.width()}x{dialog.height()}")

print("\n样式修复内容:")
print("1. ✅ 移除了 Provider List 内部的小滚动条")
print("2. ✅ General 框现在充满整个对话框")
print("3. ✅ 减少了边距和间距")
print("4. ✅ 移除了 GroupBox 的边框")

print("\n提示:")
print("- 运行此脚本查看实际效果")
print("- 检查 Provider List 是否还有内部滚动条")
print("- 检查 General 框是否充满对话框")

# 显示对话框
dialog.show()

sys.exit(app.exec())
