"""
测试邮箱插件模块导入
"""

import sys
import os

# 添加插件目录到 Python 路径
plugin_dir = os.path.dirname(os.path.abspath(__file__))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

print("测试邮箱插件模块导入...")
print("=" * 60)

try:
    # 测试导入主模块
    print("1. 测试导入 main 模块...")
    import main
    print("   ✅ main 模块导入成功")
    
    # 测试导入组件
    print("\n2. 测试导入 components 模块...")
    from components import email_list_widget
    print("   ✅ email_list_widget 导入成功")
    
    from components import email_detail_dialog
    print("   ✅ email_detail_dialog 导入成功")
    
    from components import send_email_dialog
    print("   ✅ send_email_dialog 导入成功")
    
    from components import account_config_dialog
    print("   ✅ account_config_dialog 导入成功")
    
    # 测试导入核心模块
    print("\n3. 测试导入 core 模块...")
    from core import email_client
    print("   ✅ email_client 导入成功")
    
    from core import email_parser
    print("   ✅ email_parser 导入成功")
    
    from core import email_cache
    print("   ✅ email_cache 导入成功")
    
    # 测试导入 API 模块
    print("\n4. 测试导入 api 模块...")
    from api import email_api
    print("   ✅ email_api 导入成功")
    
    # 测试导入工具模块
    print("\n5. 测试导入 utils 模块...")
    from utils import helpers
    print("   ✅ helpers 导入成功")
    
    print("\n" + "=" * 60)
    print("✅ 所有模块导入测试通过！")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ 导入失败：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
