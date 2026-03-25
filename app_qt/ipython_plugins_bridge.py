"""
IPython 插件桥接层
功能：
1. 在 IPython 中提供 plugins 变量来访问所有插件
2. 支持 plugins.list() 列出所有插件
3. 支持 plugins.call.<plugin_name>.<method>() 调用插件方法
4. 所有调用都在 UI 线程中执行，等待返回结果
"""

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
import time
import functools
import inspect


class PluginCallWrapper:
    """
    插件调用包装器
    支持链式调用：plugins.call.text_helper.get_text()
    """
    
    def __init__(self, plugin_manager, plugin_name=None):
        self.plugin_manager = plugin_manager
        self.plugin_name = plugin_name
    
    def __dir__(self):
        """返回可用的插件名称列表，用于自动补全"""
        if self.plugin_name is None:
            # 在顶层时，返回所有已加载的插件名称
            return list(self.plugin_manager.loaded_plugins.keys())
        else:
            # 在插件层级时，返回该插件的所有方法
            methods = self.plugin_manager.methods_registry.get(self.plugin_name, {})
            return list(methods.keys())
    
    def __getattr__(self, attr):
        """动态获取属性或方法"""
        # 如果是特殊方法名，返回默认实现
        if attr.startswith('_') and attr.endswith('_'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{attr}'")
        
        # 如果还没有指定插件名，返回下一个层级的包装器
        if self.plugin_name is None:
            return PluginCallWrapper(self.plugin_manager, attr)
        
        # 已经指定了插件名，现在要获取方法
        method_full_name = f"{self.plugin_name}.{attr}"
        method = self.plugin_manager.get_method(method_full_name)
        
        if method is None:
            raise AttributeError(f"插件 '{self.plugin_name}' 中没有找到方法 '{attr}'")
        
        # 返回一个包装后的调用函数，在 UI 线程中执行
        # 使用 functools.wraps 保留原始函数的签名和文档字符串
        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            return execute_in_ui_thread(method, *args, **kwargs)
        
        return wrapper


class PluginsAPI:
    """
    插件 API 接口
    提供 plugins.list() 和 plugins.call 等接口
    """
    
    def __init__(self, plugin_manager):
        self.plugin_manager = plugin_manager
        self.call = PluginCallWrapper(plugin_manager)
    
    def list(self):
        """
        列出所有已加载的插件
        
        Returns:
            dict: 插件信息字典 {plugin_name: plugin_info}
        """
        print("已加载的插件:")
        print("-" * 60)
        
        plugins_dict = {}
        for name, info in self.plugin_manager.loaded_plugins.items():
            plugin_info = {
                'name': info.get('name', name),
                'version': info.get('version', 'unknown'),
                'config': info.get('config', {}),
                'module': info.get('module', None)
            }
            plugins_dict[name] = plugin_info
            
            print(f"\n插件名称：{name}")
            print(f"版本号：{info.get('version', 'unknown')}")
            print(f"描述：{info.get('config', {}).get('description', '无')}")
            print(f"作者：{info.get('config', {}).get('author', '无')}")
            
            # 显示该插件注册的方法
            methods = self.plugin_manager.methods_registry.get(name, {})
            if methods:
                print(f"可用方法：{', '.join(methods.keys())}")
        
        print("-" * 60)
        print(f"共 {len(plugins_dict)} 个插件")
        
        return plugins_dict
    
    def info(self, plugin_name):
        """
        获取指定插件的详细信息
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            dict: 插件信息字典
        """
        if not self.plugin_manager.is_plugin_loaded(plugin_name):
            print(f"错误：插件 '{plugin_name}' 未加载")
            return None
        
        info = self.plugin_manager.get_plugin_info(plugin_name)
        print(f"\n插件信息：{plugin_name}")
        print("-" * 60)
        print(f"名称：{info.get('name', plugin_name)}")
        print(f"版本：{info.get('version', 'unknown')}")
        print(f"描述：{info.get('config', {}).get('description', '无')}")
        print(f"作者：{info.get('config', {}).get('author', '未知')}")
        
        # 显示注册的方法
        methods = self.plugin_manager.methods_registry.get(plugin_name, {})
        if methods:
            print(f"\n可用方法:")
            for method_name in methods.keys():
                print(f"  - {method_name}")
        else:
            print(f"\n没有注册公开方法")
        
        print("-" * 60)
        
        return info
    
    def methods(self, plugin_name=None):
        """
        列出插件的所有可用方法
        
        Args:
            plugin_name: 插件名称（可选），如果不提供则列出所有方法
            
        Returns:
            list or dict: 方法列表或字典
        """
        if plugin_name:
            # 列出指定插件的方法
            methods = self.plugin_manager.methods_registry.get(plugin_name, {})
            method_list = list(methods.keys())
            print(f"插件 '{plugin_name}' 的可用方法:")
            for method in method_list:
                print(f"  - {method}")
            return method_list
        else:
            # 列出所有插件的方法
            all_methods = {}
            for namespace, methods in self.plugin_manager.methods_registry.items():
                all_methods[namespace] = list(methods.keys())
            
            print("所有已注册的方法:")
            print("-" * 60)
            for namespace, methods in all_methods.items():
                print(f"\n{namespace}:")
                for method in methods:
                    print(f"  - {method}")
            print("-" * 60)
            
            return all_methods
    
    def reload(self, plugin_name: str = None):
        """
        热加载插件
        
        Args:
            plugin_name: 插件名称，如果不提供则列出所有可重载的插件
            
        Returns:
            bool: 是否成功（仅当指定插件名称时）
        """
        if plugin_name is None:
            # 列出所有可重载的插件
            reloadable = self.plugin_manager.get_reloadable_plugins()
            print("可热加载的插件列表:")
            print("-" * 60)
            if reloadable:
                for name in reloadable:
                    info = self.plugin_manager.get_plugin_info(name)
                    version = info.get('version', 'unknown') if info else 'unknown'
                    print(f"  - {name} (v{version})")
                print("-" * 60)
                print(f"\n使用方法: plugins.reload('plugin_name')")
            else:
                print("  没有已加载的插件")
            print("-" * 60)
            return reloadable
        
        # 执行热重载
        print(f"\n开始热加载插件: {plugin_name}")
        print("-" * 60)
        
        success = execute_in_ui_thread(
            lambda: self.plugin_manager.reload_plugin(plugin_name)
        )
        
        if success:
            print(f"✅ 插件 '{plugin_name}' 热加载成功！")
        else:
            print(f"❌ 插件 '{plugin_name}' 热加载失败！")
        print("-" * 60)
        
        return success
    
    def ui_elements(self, plugin_name: str = None):
        """
        查看插件注册的 UI 元素
        
        Args:
            plugin_name: 插件名称（可选），如果不提供则列出所有插件的 UI 元素
            
        Returns:
            list: UI 元素列表
        """
        if plugin_name:
            # 查看指定插件的 UI 元素
            elements = self.plugin_manager.ui_elements_registry.get(plugin_name, [])
            print(f"插件 '{plugin_name}' 注册的 UI 元素:")
            print("-" * 60)
            if elements:
                for elem in elements:
                    print(f"  [{elem['type']}] {elem['name']}")
            else:
                print("  没有注册的 UI 元素")
            print("-" * 60)
            return elements
        else:
            # 列出所有插件的 UI 元素
            all_elements = {}
            for name, elements in self.plugin_manager.ui_elements_registry.items():
                all_elements[name] = [
                    {"type": e["type"], "name": e["name"]} 
                    for e in elements
                ]
            
            print("所有插件注册的 UI 元素:")
            print("-" * 60)
            for name, elements in all_elements.items():
                print(f"\n{name}:")
                if elements:
                    for elem in elements:
                        print(f"  [{elem['type']}] {elem['name']}")
                else:
                    print("  (无)")
            print("-" * 60)
            
            return all_elements


# ==================== UI 线程执行机制 ====================

class UIThreadExecutor(QObject):
    """UI 线程执行器"""
    
    result_ready = Signal(object)  # 发射执行结果
    
    def __init__(self):
        super().__init__()
        self.result = None
        self.completed = False
    
    def execute(self, func, *args, **kwargs):
        """在 UI 线程中执行函数"""
        self.result = None
        self.completed = False
        
        # 使用 QTimer 在主线程中执行
        from PySide6.QtCore import QTimer
        
        executor = self
        
        def run_func():
            try:
                result = func(*args, **kwargs)
                executor.result = result
                executor.completed = True
                executor.result_ready.emit(result)
            except Exception as e:
                executor.result = e
                executor.completed = True
                executor.result_ready.emit(e)
        
        # 将函数调度到主线程执行
        QTimer.singleShot(0, run_func)


def execute_in_ui_thread(func, *args, timeout=5.0, **kwargs):
    """
    在 UI 线程中执行函数并等待结果
    
    Args:
        func: 要执行的函数
        *args: 函数参数
        timeout: 超时时间（秒）
        **kwargs: 关键字参数
        
    Returns:
        函数执行结果
        
    Raises:
        Exception: 函数执行异常或超时
    """
    # 检查是否在 IPython 环境中
    app = QApplication.instance()
    if app is None:
        # 不在 Qt 应用中，直接调用
        print("[警告] 不在 Qt 应用环境中，直接调用函数")
        return func(*args, **kwargs)
    
    # 创建执行器
    executor = UIThreadExecutor()
    
    # 在 UI 线程中执行
    from PySide6.QtCore import QTimer
    QTimer.singleShot(0, lambda: _run_in_ui_thread(func, args, kwargs, executor))
    
    # 等待结果（使用事件循环）
    start_time = time.time()
    while not executor.completed:
        # 处理事件循环
        app.processEvents()
        time.sleep(0.01)
        
        # 检查超时
        if time.time() - start_time > timeout:
            raise TimeoutError(f"UI 线程执行超时（{timeout}秒）")
    
    # 检查结果
    if isinstance(executor.result, Exception):
        raise executor.result
    
    return executor.result


def _run_in_ui_thread(func, args, kwargs, executor):
    """在 UI 线程中运行函数的内部实现"""
    try:
        result = func(*args, **kwargs)
        executor.result = result
        executor.completed = True
        executor.result_ready.emit(result)
    except Exception as e:
        executor.result = e
        executor.completed = True
        executor.result_ready.emit(e)


# ==================== 初始化函数 ====================

def init_ipython_plugins_api(plugin_manager):
    """
    初始化 IPython 插件 API
    
    Args:
        plugin_manager: 插件管理器实例
        
    Returns:
        PluginsAPI: 插件 API 对象
    """
    # 创建 API 对象
    plugins_api = PluginsAPI(plugin_manager)
    
    print("\n" + "=" * 60)
    print("IPython 插件 API 已初始化")
    print("=" * 60)
    print("\n使用方法:")
    print("  plugins.list()              - 列出所有插件")
    print("  plugins.info('plugin')      - 查看插件详细信息")
    print("  plugins.methods()           - 列出所有方法")
    print("  plugins.methods('plugin')   - 列出指定插件的方法")
    print("  plugins.reload()            - 列出可热加载的插件")
    print("  plugins.reload('plugin')    - 热加载指定插件")
    print("  plugins.ui_elements()       - 列出所有 UI 元素")
    print("  plugins.ui_elements('plugin') - 列出指定插件的 UI 元素")
    print("  plugins.call.plugin_name.method_name() - 调用插件方法")
    print("\n示例:")
    print("  >>> plugins.list()")
    print("  >>> plugins.reload('text_helper')")
    print("  >>> plugins.call.text_helper.get_text()")
    print("  >>> plugins.call.text_helper.set_text('Hello World')")
    print("=" * 60 + "\n")
    
    return plugins_api
