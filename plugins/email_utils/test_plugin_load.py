"""
测试邮箱插件加载
模拟插件管理器的加载逻辑
"""

import sys
import os
import importlib.util
import json

# 插件路径
plugin_path = os.path.dirname(os.path.abspath(__file__))
plugin_json_path = os.path.join(plugin_path, "plugin.json")

print("=" * 60)
print("测试邮箱插件加载...")
print("=" * 60)

try:
    # 读取 plugin.json
    with open(plugin_json_path, "r", encoding="utf-8") as f:
        plugin_config = json.load(f)
    
    plugin_name = plugin_config.get("name")
    print(f"\n插件名称：{plugin_name}")
    
    # 找到入口模块
    main_module = plugin_config.get("main", "main")
    main_py_path = os.path.join(plugin_path, f"{main_module}.py")
    print(f"入口文件：{main_py_path}")
    
    if not os.path.exists(main_py_path):
        raise FileNotFoundError(f"找不到插件入口文件：{main_py_path}")
    
    # 动态导入插件模块 - 将整个插件目录作为包导入
    print("\n正在导入插件模块...")
    spec = importlib.util.spec_from_file_location(
        f"plugin_{plugin_name}", main_py_path,
        submodule_search_locations=[plugin_path]  # 关键：指定子模块搜索路径
    )
    
    if spec is None:
        raise ImportError(f"无法创建模块规范：{main_py_path}")
    
    plugin_module = importlib.util.module_from_spec(spec)
    sys.modules[f"plugin_{plugin_name}"] = plugin_module  # 注册到 sys.modules
    spec.loader.exec_module(plugin_module)
    
    print("✅ 插件模块导入成功！")
    
    # 执行加载函数
    if hasattr(plugin_module, "load_plugin"):
        print("\n调用 load_plugin 函数...")
        # 这里不真正调用，因为需要 plugin_manager 实例
        print("✅ load_plugin 函数存在")
    else:
        raise Exception(f"插件 {plugin_name} 缺少 load_plugin 函数")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！插件可以正常加载。")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ 测试失败：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
