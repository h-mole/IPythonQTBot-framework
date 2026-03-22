"""
测试嵌套的 List[BaseSettings] 功能
"""
import sys
sys.path.append(r"C:\Users\hzy\Programs\myhelper")
sys.path.append(r"C:\Users\hzy\Programs\myhelper\pyside6-settings")

from app_qt.configs import MainAppConfigSettings, LLMProvider
from PySide6.QtWidgets import QApplication, QMainWindow
import json


# Create Qt application
app = QApplication([])

# 创建带有默认 provider 的配置
default_settings = {
    "llm_config": {
        "provider": "",
        "model": "glm-4",
        "max_context_messages": 10,
        "customization_name": "default",
        "provider_list": [
            {"name": "openai", "api_key": "sk-xxx", "api_url": "https://api.openai.com/v1"},
            {"name": "zhipu", "api_key": "xxx", "api_url": "https://open.bigmodel.cn/api/paas/v4"}
        ]
    }
}

print("初始配置:")
print(json.dumps(default_settings, indent=2, ensure_ascii=False))

# 保存到临时文件
with open("test_nested_config.json", "w", encoding="utf-8") as f:
    json.dump(default_settings, f, indent=2, ensure_ascii=False)

# 从文件加载配置
settings = MainAppConfigSettings.load(config_file="test_nested_config.json")

print("\n从文件加载后的配置:")
print(f"LLM Config Provider List 长度：{len(settings.llm_config.provider_list)}")
for i, provider in enumerate(settings.llm_config.provider_list):
    print(f"  [{i}] {provider.name}: {provider.api_url}")

# 创建主窗口显示配置表单
window = QMainWindow()
window.setCentralWidget(settings.create_form())
window.setWindowTitle("嵌套设置测试 - MainAppConfigSettings")
window.resize(900, 700)
window.show()

print("\n界面已打开，您可以:")
print("1. 在 'Llm Config' 组中找到 'Provider List'")
print("2. 点击 '+ 添加' 按钮添加新的 provider")
print("3. 点击每个 provider 的 '删除' 按钮删除该 provider")
print("4. 修改任意字段，更改会自动保存到 test_nested_config.json")
print("\n按 Ctrl+C 退出程序...")

try:
    app.exec()
except KeyboardInterrupt:
    print("\n程序已退出")
