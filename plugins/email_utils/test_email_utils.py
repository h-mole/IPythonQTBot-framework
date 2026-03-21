"""
测试邮箱工具插件
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 设置环境变量以便导入
os.environ['PYTHONPATH'] = project_root

# 现在可以导入 configs
from app_qt.configs import PLUGIN_DATA_DIR

def test_config_structure():
    """测试配置文件结构"""
    print("=" * 60)
    print("测试配置文件结构")
    print("=" * 60)
    
    # 配置文件应该在插件目录下的 data 文件夹
    config_dir = os.path.join(os.path.dirname(__file__), "data")
    config_file = os.path.join(config_dir, "email_accounts.json")
    
    print(f"\n配置目录：{config_dir}")
    print(f"配置文件：{config_file}")
    
    # 确保目录存在
    os.makedirs(config_dir, exist_ok=True)
    print(f"✓ 已创建配置目录")
    
    # 检查配置文件是否存在
    if not os.path.exists(config_file):
        print("⚠ 配置文件不存在，需要运行 init_data.py 创建示例配置")
        return False
    
    import json
    with open(config_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 验证配置结构
    if "accounts" not in data:
        print("✗ 配置文件中缺少 'accounts' 字段")
        return False
    
    accounts = data["accounts"]
    print(f"\n找到 {len(accounts)} 个配置的账号")
    
    # 验证每个账号的必需字段
    required_fields = ["name", "username", "password", "imap_server", "imap_port", 
                      "smtp_server", "smtp_port", "use_ssl"]
    
    for i, account in enumerate(accounts):
        print(f"\n账号 {i+1}: {account.get('name', '未命名')}")
        
        missing_fields = []
        for field in required_fields:
            if field not in account:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"  ✗ 缺少字段：{', '.join(missing_fields)}")
        else:
            print(f"  ✓ 所有必需字段都存在")
            print(f"    - 邮箱地址：{account.get('username')}")
            print(f"    - IMAP: {account.get('imap_server')}:{account.get('imap_port')}")
            print(f"    - SMTP: {account.get('smtp_server')}:{account.get('smtp_port')}")
            print(f"    - SSL: {'是' if account.get('use_ssl') else '否'}")
    
    return True


def test_imports():
    """测试必要的依赖是否安装"""
    print("\n" + "=" * 60)
    print("测试依赖包")
    print("=" * 60)
    
    dependencies = {
        'PySide6': 'pyside6',
        'imaplib': 'imaplib (标准库)',
        'smtplib': 'smtplib (标准库)',
        'email': 'email (标准库)',
        'bs4': 'beautifulsoup4',
    }
    
    results = {}
    for module, package_name in dependencies.items():
        try:
            __import__(module)
            print(f"✓ {package_name} 已安装")
            results[module] = True
        except ImportError as e:
            print(f"✗ {package_name} 未安装：{e}")
            results[module] = False
    
    return all(results.values())


def test_plugin_metadata():
    """测试插件元数据"""
    print("\n" + "=" * 60)
    print("测试插件元数据")
    print("=" * 60)
    
    plugin_json_path = os.path.join(os.path.dirname(__file__), "plugin.json")
    
    if not os.path.exists(plugin_json_path):
        print(f"✗ plugin.json 不存在：{plugin_json_path}")
        return False
    
    import json
    with open(plugin_json_path, "r", encoding="utf-8") as f:
        plugin_data = json.load(f)
    
    # 验证必需字段
    required_fields = ["name", "description", "version", "main", "tabs"]
    
    for field in required_fields:
        if field not in plugin_data:
            print(f"✗ 缺少必需字段：{field}")
            return False
        else:
            print(f"✓ {field}: {plugin_data[field]}")
    
    # 验证导出方法
    if "exports" in plugin_data:
        exports = plugin_data["exports"]
        print(f"\n导出配置:")
        print(f"  命名空间：{exports.get('namespace')}")
        print(f"  方法数量：{len(exports.get('methods', []))}")
        
        for method in exports.get('methods', []):
            print(f"    - {method['name']}: {method['description']}")
            
            # 检查 MCP 支持
            if method.get('extra_data', {}).get('enable_mcp'):
                print(f"      ✓ 支持 MCP")
    
    # 验证标签页
    tabs = plugin_data.get("tabs", [])
    print(f"\n标签页:")
    for tab in tabs:
        print(f"  - {tab['name']} (位置：{tab.get('position', '默认')})")
    
    return True


def test_main_module():
    """测试主模块导入"""
    print("\n" + "=" * 60)
    print("测试主模块导入")
    print("=" * 60)
    
    try:
        from plugins.email_utils import EmailManagerTab, load_plugin, unload_plugin
        print("✓ 成功导入 EmailManagerTab")
        print("✓ 成功导入 load_plugin")
        print("✓ 成功导入 unload_plugin")
        return True
    except Exception as e:
        print(f"✗ 导入失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("邮箱工具插件测试")
    print("=" * 60)
    
    tests = [
        ("依赖包检查", test_imports),
        ("插件元数据检查", test_plugin_metadata),
        ("主模块导入检查", test_main_module),
        ("配置文件检查", test_config_structure),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            result = test_func()
            results[name] = result
        except Exception as e:
            print(f"\n{name} 发生异常：{e}")
            import traceback
            traceback.print_exc()
            results[name] = False
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 所有测试通过！")
        print("\n下一步:")
        print("1. 运行 python init_data.py 初始化配置文件（如果还没有）")
        print("2. 编辑 email_accounts.json 填入真实的邮箱账号信息")
        print("3. 启动主程序测试插件功能")
    else:
        print("\n⚠ 部分测试失败，请检查上述错误信息")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
