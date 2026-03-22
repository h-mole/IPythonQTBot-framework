"""
测试设置面板功能
"""

import sys
sys.path.append(r"C:\Users\hzy\Programs\myhelper")

from PySide6.QtWidgets import QApplication
from app_qt.configs import settings
from app_qt.widgets.settings_panel import SettingsDialog, check_and_show_unconfigured_dialog

# Create Qt application
app = QApplication([])

print("=" * 50)
print("测试设置面板功能")
print("=" * 50)

# 检查配置状态
is_configured = settings.is_provider_configured()
print(f"\n当前配置状态：{'已配置' if is_configured else '未配置'}")
print(f"提供商：{settings.llm_config.provider}")
print(f"提供商列表数量：{len(settings.llm_config.provider_list)}")

# 创建设置对话框
print("\n创建设置对话框...")
dialog = SettingsDialog(settings)
dialog.show()

print("\n设置对话框已显示")
print("提示：")
print("- 如果未配置，会看到空白的提供商列表")
print("- 可以点击'添加'按钮添加新的提供商")
print("- 填写完成后点击'保存配置'按钮")
print("- 关闭程序窗口退出测试")

# 运行应用
sys.exit(app.exec())
