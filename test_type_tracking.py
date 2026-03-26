#!/usr/bin/env python3
"""测试类型追踪功能的示例文件"""

from app_qt.plugin_manager import PluginManager, get_plugin_manager


# 方式1: 通过 get_plugin_manager() 获取
pm = get_plugin_manager()
pm.register_method("test", "method1", lambda: None)

# 方式2: 类型注解
manager: PluginManager = get_plugin_manager()
manager.register_method("test", "method2", lambda: None)
result = manager.get_method("test.method2")


def test_function(plugin_manager: PluginManager):
    """方式3: 函数参数类型注解"""
    plugin_manager.register_method("test", "method3", lambda: None)
    plugin_manager.get_method("test.method3")


class MyClass:
    def __init__(self):
        # 方式4: self.plugin_manager
        self.plugin_manager = get_plugin_manager()
    
    def do_something(self):
        self.plugin_manager.register_method("test", "method4", lambda: None)
        method = self.plugin_manager.get_method("test.method4")


# 测试使用变量（应该发出警告）
def test_with_variable(pm_instance: PluginManager):
    method_name = "dynamic_method"
    pm_instance.get_method(method_name)  # 使用变量，无法解析


# 其他类的 get_method 调用（不应该被追踪）
class OtherClass:
    def get_method(self, name):
        pass


other = OtherClass()
other.get_method("something")  # 这个不应该被追踪
