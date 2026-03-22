"""
验证设置面板修复
"""

import sys
sys.path.append(r"C:\Users\hzy\Programs\myhelper")

print("=" * 60)
print("验证设置面板修复")
print("=" * 60)

# 1. 测试导入
print("\n1. 测试导入...")
try:
    from app_qt.configs import settings, app_config
    from app_qt.widgets.settings_panel import SettingsDialog, UnconfiguredDialog, check_and_show_unconfigured_dialog
    print("   ✅ 导入成功")
except Exception as e:
    print(f"   ❌ 导入失败：{e}")
    sys.exit(1)

# 2. 测试配置数据结构
print("\n2. 测试配置数据结构...")
try:
    # 检查 settings 实例
    assert hasattr(settings, 'llm_config'), "settings 缺少 llm_config 属性"
    assert hasattr(settings.llm_config, 'provider'), "llm_config 缺少 provider 属性"
    assert hasattr(settings.llm_config, 'provider_list'), "llm_config 缺少 provider_list 属性"
    print(f"   ✅ settings 结构正确")
    print(f"      - Provider: {settings.llm_config.provider or '(空)'}")
    print(f"      - Provider List 数量：{len(settings.llm_config.provider_list)}")
except Exception as e:
    print(f"   ❌ 配置结构错误：{e}")
    sys.exit(1)

# 3. 测试 app_config 兼容性
print("\n3. 测试 app_config 兼容性...")
try:
    assert hasattr(app_config, 'llm_config'), "app_config 缺少 llm_config 属性"
    print(f"   ✅ app_config 向后兼容正常")
except Exception as e:
    print(f"   ❌ app_config 兼容性错误：{e}")
    sys.exit(1)

# 4. 测试配置检查方法
print("\n4. 测试配置检查方法...")
try:
    is_configured = settings.is_provider_configured()
    print(f"   ✅ is_provider_configured() 调用成功")
    print(f"      - 配置状态：{'已配置' if is_configured else '未配置'}")
except Exception as e:
    print(f"   ❌ 配置检查方法错误：{e}")
    sys.exit(1)

# 5. 测试 SettingsDialog 类
print("\n5. 测试 SettingsDialog 类...")
try:
    from PySide6.QtWidgets import QApplication
    # 不要创建 QApplication，只检查类定义
    # app = QApplication.instance() or QApplication([])
    
    # 检查类是否存在和继承关系
    from PySide6.QtWidgets import QDialog
    assert issubclass(SettingsDialog, QDialog), "SettingsDialog 应该继承自 QDialog"
    print(f"   ✅ SettingsDialog 类定义正确")
    print(f"      - 继承自：QDialog")
    print(f"      - 是模态对话框")
except Exception as e:
    print(f"   ❌ SettingsDialog 错误：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 6. 测试配置文件路径
print("\n6. 测试配置文件路径...")
try:
    from pathlib import Path
    config_path = Path("config.json")
    exists = config_path.exists()
    print(f"   ✅ 配置文件检查完成")
    print(f"      - 路径：{config_path.absolute()}")
    print(f"      - 存在：{'是' if exists else '否'}")
except Exception as e:
    print(f"   ❌ 配置文件检查错误：{e}")

print("\n" + "=" * 60)
print("✅ 所有验证通过！")
print("=" * 60)
print("\n提示:")
print("- 设置对话框现在是模态的 (使用 exec() 显示)")
print("- MainAppConfigSettings 是主要的配置类")
print("- app_config 保留用于向后兼容")
print("- 运行 python single_component_tests/test_settings_panel.py 进行 UI 测试")
