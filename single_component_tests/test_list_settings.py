"""
测试 List[BaseSettings] 类型的动态组件功能
"""
import sys
sys.path.append(r"C:\Users\hzy\Programs\myhelper")
sys.path.append(r"C:\Users\hzy\Programs\myhelper\pyside6-settings")

from app_qt.configs import LLMProvider, LLMConfigSettings
from PySide6.QtWidgets import QApplication, QMainWindow
import json


# Create Qt application
app = QApplication([])

# 创建带有默认 provider 的配置
default_settings = {
    "provider": "",
    "model": "glm-4",
    "max_context_messages": 10,
    "customization_name": "default",
    "provider_list": [
        {"name": "openai", "api_key": "sk-xxx", "api_url": "https://api.openai.com/v1"},
        {"name": "zhipu", "api_key": "xxx", "api_url": "https://open.bigmodel.cn/api/paas/v4"}
    ]
}

print("初始配置:")
print(json.dumps(default_settings, indent=2, ensure_ascii=False))

# 保存到临时文件
with open("test_config.json", "w", encoding="utf-8") as f:
    json.dump(default_settings, f, indent=2, ensure_ascii=False)

# 从文件加载配置
settings = LLMConfigSettings.load(config_file="test_config.json")

print("\n从文件加载后的配置:")
print(f"Provider List 长度：{len(settings.provider_list)}")
for i, provider in enumerate(settings.provider_list):
    print(f"  [{i}] {provider.name}: {provider.api_url}")

# 创建主窗口显示配置表单
window = QMainWindow()
window.setCentralWidget(settings.create_form())
window.setWindowTitle("LLM 配置设置 - 测试 List[BaseSettings] 动态组件")
window.resize(800, 600)
window.show()

print("\n界面已打开，您可以:")
print("1. 点击 '+ 添加' 按钮添加新的 provider")
print("2. 点击每个 provider 的 '删除' 按钮删除该 provider")
print("3. 修改任意字段，更改会自动保存到 test_config.json")
print("\n按 Ctrl+C 退出程序...")

try:
    app.exec()
except KeyboardInterrupt:
    print("\n程序已退出")
