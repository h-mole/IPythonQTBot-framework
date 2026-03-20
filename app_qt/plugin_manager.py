"""
插件管理器 - 核心框架
功能：
1. 插件加载/卸载管理
2. 方法注册表（命名空间机制）
3. 插件生命周期管理
4. UI 组件注入（标签页、菜单）
"""

import os
import sys
import json
import importlib.util
import re
from typing import Callable, Optional, Any
from typing_extensions import TypedDict
from PySide6.QtWidgets import QMenuBar
from PySide6.QtCore import QObject

# 导入配置
from app_qt.configs import PLUGINS_DIR, PLUGINS_CONFIG_FILE


# ============ TypedDict 类型定义 ============

class MethodExtraData(TypedDict, total=False):
    """
    方法额外数据配置
    
    Attributes:
        enable_mcp: 是否启用 MCP (Model Context Protocol)
        allow_remote_call: 是否允许远程调用
        rate_limit: 调用频率限制（次/分钟）
        timeout: 超时时间（秒）
        retry_count: 重试次数
        tags: 标签列表
        metadata: 其他元数据
    """
    enable_mcp: bool
    allow_remote_call: bool
    rate_limit: int
    timeout: float
    retry_count: int
    tags: list
    metadata: dict[str, Any]


class MethodInfo(TypedDict, total=False):
    """
    方法信息结构
    
    Attributes:
        name: 方法名称
        description: 方法描述
        stable: 是否稳定版本
        parameters: 参数列表
        returns: 返回值信息
        extra_data: 额外数据配置
    """
    name: str
    description: str
    stable: bool
    parameters: list[dict[str, Any]]
    returns: dict[str, Any]
    extra_data: MethodExtraData


class PluginExports(TypedDict, total=False):
    """
    插件导出配置
    
    Attributes:
        namespace: 命名空间
        description: 描述
        methods: 方法列表
    """
    namespace: str
    description: str
    methods: list[MethodInfo]


class PluginConfig(TypedDict, total=False):
    """
    插件配置结构
    
    Attributes:
        name: 插件名称
        description: 插件描述
        version: 版本号
        author: 作者
        main: 入口模块
        dependencies: 依赖列表
        exports: 导出配置
        callbacks: 回调函数配置
        tabs: 标签页配置
    """
    name: str
    description: str
    version: str
    author: str
    main: str
    dependencies: list[dict[str, Any]]
    exports: PluginExports
    callbacks: dict[str, str]
    tabs: list[dict[str, Any]]


class RegisteredMethod(TypedDict):
    """
    已注册的方法信息
    
    Attributes:
        func: 方法对象
        plugin_name: 插件名称
        method_info: 方法信息（来自 plugin.json）
        extra_data: 额外数据配置
    """
    func: Callable
    plugin_name: str
    method_info: Optional[MethodInfo]
    extra_data: Optional[MethodExtraData]


class PluginManager(QObject):
    """
    插件管理器（单例模式）

    核心功能：
    - 加载和卸载插件
    - 注册和管理插件暴露的方法
    - 添加插件标签页和菜单
    - 管理插件启用状态
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = PluginManager()
        return cls._instance

    def __init__(self):
        super().__init__()
        if PluginManager._instance is not None:
            raise Exception("PluginManager 是单例，请使用 get_instance() 获取实例")

        # 方法注册表：{namespace: {method_name: func}}
        self.methods_registry = {}

        # 已加载的插件：{plugin_name: plugin_info}
        self.loaded_plugins = {}

        # 方法元数据缓存：{namespace: {method_name: method_info_from_json}}
        self.methods_metadata_cache = {}

        # 待添加的标签页列表
        self.pending_tabs = []

        # 主窗口引用（在初始化时设置）
        self.main_window = None
        self.notebook = None
        self.menu_bar = None

        # 系统依赖缓存（避免重复检查）
        self.system_dependencies_cache = {}

    def set_main_window(self, main_window, notebook, menu_bar):
        """
        设置主窗口引用

        Args:
            main_window: 主窗口对象
            notebook: 标签页控件
            menu_bar: 菜单栏
        """
        self.main_window = main_window
        self.notebook = notebook
        self.menu_bar = menu_bar
        # 添加待处理的标签页
        self._add_pending_tabs()

    def _add_pending_tabs(self):
        """添加待处理的标签页"""
        for tab_info in self.pending_tabs:
            try:
                position = tab_info.get("position")
                if position is not None:
                    self.notebook.insertTab(
                        position, tab_info["instance"], tab_info["name"]
                    )
                else:
                    self.notebook.addTab(tab_info["instance"], tab_info["name"])
                print(
                    f"[PluginManager] 已添加插件标签页：{tab_info['name']} (插件：{tab_info['plugin_name']})"
                )
            except Exception as e:
                print(f"[PluginManager] 添加标签页失败：{tab_info['name']}, 错误：{e}")

        self.pending_tabs.clear()

    def load_plugins(self):
        """加载所有启用的插件（基于依赖关系排序）"""
        print("[PluginManager] 开始加载插件...")

        # 确保插件目录存在
        if not os.path.exists(PLUGINS_DIR):
            print(f"[PluginManager] 插件目录不存在：{PLUGINS_DIR}")
            return

        # 读取插件配置
        plugins_config = self._load_plugins_config()

        # 扫描并收集所有插件信息
        plugin_infos = self._scan_all_plugins(plugins_config)

        # 解析依赖关系并排序
        sorted_plugins = self._resolve_plugin_dependencies(plugin_infos)

        # 按顺序加载插件
        loaded_count = 0
        for plugin_name, plugin_info in sorted_plugins:
            try:
                self._load_single_plugin(
                    plugin_info["path"], plugin_info["config_path"]
                )
                loaded_count += 1
            except Exception as e:
                print(f"[PluginManager] 加载插件失败：{plugin_name}, 错误：{e}")
                import traceback

                traceback.print_exc()

        print(f"[PluginManager] 插件加载完成，共加载 {loaded_count} 个插件")

    def _scan_all_plugins(self, plugins_config):
        """
        扫描所有启用的插件并收集信息

        Args:
            plugins_config: 插件配置文件

        Returns:
            dict: {plugin_name: {path, config_path, config, enabled}}
        """
        plugin_infos = {}

        for plugin_name in os.listdir(PLUGINS_DIR):
            plugin_path = os.path.join(PLUGINS_DIR, plugin_name)

            # 只处理目录
            if not os.path.isdir(plugin_path):
                continue

            # 检查是否有 plugin.json
            plugin_json_path = os.path.join(plugin_path, "plugin.json")
            if not os.path.exists(plugin_json_path):
                continue

            # 检查是否启用
            if not self._is_plugin_enabled(plugin_name, plugins_config):
                print(f"[PluginManager] 插件未启用：{plugin_name}")
                continue

            # 读取配置
            try:
                with open(plugin_json_path, "r", encoding="utf-8") as f:
                    config = json.load(f)

                plugin_infos[plugin_name] = {
                    "name": plugin_name,
                    "path": plugin_path,
                    "config_path": plugin_json_path,
                    "config": config,
                    "enabled": True,
                }
            except Exception as e:
                print(f"[PluginManager] 读取插件配置失败：{plugin_name}, 错误：{e}")

        return plugin_infos

    def _resolve_plugin_dependencies(self, plugin_infos):
        """
        解析插件依赖关系并排序

        Args:
            plugin_infos: 所有插件信息字典

        Returns:
            list: 排序后的插件列表 [(plugin_name, plugin_info), ...]

        Raises:
            Exception: 当存在循环依赖或依赖不满足时
        """
        # 已加载的插件集合
        loaded_set = set()

        # 待加载的插件队列
        pending_queue = list(plugin_infos.items())

        # 排序后的结果
        sorted_plugins = []

        # 最大迭代次数（防止死循环）
        max_iterations = len(pending_queue) * 2
        iteration_count = 0

        while pending_queue and iteration_count < max_iterations:
            iteration_count += 1
            progress_made = False

            # 遍历待加载队列
            remaining_queue = []

            for plugin_name, plugin_info in pending_queue:
                # 获取依赖列表
                dependencies = plugin_info["config"].get("dependencies", [])

                # 检查所有依赖是否满足
                deps_satisfied = True
                missing_deps = []

                for dep in dependencies:
                    dep_name = dep.get("name", "")
                    required = dep.get("required", True)

                    # 只处理插件依赖（system: 开头的在加载时检查）
                    if not dep_name.startswith("plugin:"):
                        continue

                    # 去掉 "plugin:" 前缀
                    required_plugin = dep_name[7:]

                    # 检查依赖插件是否已加载
                    if required_plugin not in loaded_set:
                        if required:
                            deps_satisfied = False
                            missing_deps.append(required_plugin)
                        else:
                            # 可选依赖，记录警告
                            print(
                                f"[PluginManager] 警告：{plugin_name} 的可选依赖 {required_plugin} 未加载"
                            )

                if deps_satisfied:
                    # 依赖满足，可以加载
                    sorted_plugins.append((plugin_name, plugin_info))
                    loaded_set.add(plugin_name)
                    progress_made = True
                else:
                    # 依赖不满足，加入等待队列
                    remaining_queue.append((plugin_name, plugin_info))

            # 更新待加载队列
            pending_queue = remaining_queue

            # 如果本轮没有进展，说明有循环依赖或无法满足的依赖
            if not progress_made and pending_queue:
                # 输出未加载的插件
                unmet_plugins = [name for name, _ in pending_queue]
                raise Exception(
                    f"插件依赖无法满足或存在循环依赖。\n"
                    f"未加载的插件：{', '.join(unmet_plugins)}\n"
                    f"已加载的插件：{', '.join(loaded_set)}"
                )

        # 检查是否还有未加载的插件
        if pending_queue:
            unmet_plugins = [name for name, _ in pending_queue]
            raise Exception(
                f"部分插件无法加载（可能超过最大迭代次数）。\n"
                f"未加载的插件：{', '.join(unmet_plugins)}"
            )

        return sorted_plugins

    def _load_plugins_config(self):
        """读取插件配置文件"""
        if not os.path.exists(PLUGINS_CONFIG_FILE):
            # 创建默认配置
            default_config = {
                "plugins": [],
                "settings": {
                    "auto_load_new_plugins": True,
                    "allow_disable_builtin": False,
                },
            }

            # 确保目录存在
            os.makedirs(os.path.dirname(PLUGINS_CONFIG_FILE), exist_ok=True)

            # 写入默认配置
            with open(PLUGINS_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)

            return default_config

        try:
            with open(PLUGINS_CONFIG_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            print(f"[PluginManager] 读取配置文件失败：{e}")
            return {"plugins": [], "settings": {"auto_load_new_plugins": True}}

    def _is_plugin_enabled(self, plugin_name, plugins_config):
        """检查插件是否启用"""
        # 如果配置允许自动加载新插件，且没有明确禁用，则启用
        auto_load = plugins_config.get("settings", {}).get(
            "auto_load_new_plugins", True
        )

        # 查找插件配置
        for plugin_cfg in plugins_config.get("plugins", []):
            if plugin_cfg.get("name") == plugin_name:
                return plugin_cfg.get("enabled", True)

        # 新插件，根据配置决定是否自动加载
        if auto_load:
            # 添加到配置文件
            plugins_config["plugins"].append(
                {"name": plugin_name, "enabled": True, "version": "unknown"}
            )

            # 保存配置
            with open(PLUGINS_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(plugins_config, f, indent=2, ensure_ascii=False)

            return True

        return False

    def _load_single_plugin(self, plugin_path, plugin_json_path):
        """加载单个插件"""
        # 读取 plugin.json
        with open(plugin_json_path, "r", encoding="utf-8") as f:
            plugin_config = json.load(f)

        plugin_name = plugin_config.get("name")
        plugin_version = plugin_config.get("version", "1.0.0")

        print(f"[PluginManager] 正在加载插件：{plugin_name} v{plugin_version}")

        # 检查依赖
        dependencies = plugin_config.get("dependencies", [])
        if dependencies:
            deps_result = self._check_plugin_dependencies(dependencies, plugin_name)
            if not deps_result["success"]:
                raise Exception(f"依赖检查失败：{deps_result['error']}")

        # 找到入口模块
        main_module = plugin_config.get("main", "main")
        main_py_path = os.path.join(plugin_path, f"{main_module}.py")

        if not os.path.exists(main_py_path):
            raise FileNotFoundError(f"找不到插件入口文件：{main_py_path}")

        # 动态导入插件模块
        spec = importlib.util.spec_from_file_location(
            f"plugin_{plugin_name}", main_py_path
        )
        plugin_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin_module)

        # 执行加载函数
        if hasattr(plugin_module, "load_plugin"):
            result = plugin_module.load_plugin(self)

            # 缓存方法的元数据（从 plugin.json 的 exports.methods）
            exports = plugin_config.get("exports", {})
            methods_list = exports.get("methods", [])
            namespace = exports.get("namespace", plugin_name)
            
            # 构建方法元数据缓存
            self.methods_metadata_cache[namespace] = {}
            for method_info in methods_list:
                method_name = method_info.get("name")
                if method_name:
                    self.methods_metadata_cache[namespace][method_name] = method_info

            # 记录已加载的插件
            self.loaded_plugins[plugin_name] = {
                "name": plugin_name,
                "version": plugin_version,
                "module": plugin_module,
                "config": plugin_config,
                "result": result,
            }

            print(f"[PluginManager] 插件 {plugin_name} 加载成功")
        else:
            raise Exception(f"插件 {plugin_name} 缺少 load_plugin 函数")

    def _check_plugin_dependencies(self, dependencies, plugin_name):
        """
        检查插件依赖是否满足

        Args:
            dependencies: 依赖列表，格式：
                        [{"name": "system:pandoc", "version": ">=2.0", "required": True}, ...]
            plugin_name: 插件名称

        Returns:
            dict: {"success": bool, "error": str or None}
        """
        for dep in dependencies:
            dep_name = dep.get("name", "")
            dep_version = dep.get("version", "*")
            required = dep.get("required", True)

            # 检查系统依赖
            if dep_name.startswith("system:"):
                system_tool = dep_name[7:]  # 去掉 "system:" 前缀

                # 检查工具是否存在
                if not self._check_system_tool_exists(system_tool):
                    if required:
                        return {
                            "success": False,
                            "error": f"缺少系统依赖：{system_tool}，请安装后重试",
                        }
                    else:
                        print(
                            f"[PluginManager] 警告：插件 {plugin_name} 的非必需依赖 {system_tool} 未安装"
                        )
                        continue

                # 检查版本
                if dep_version and dep_version != "*":
                    actual_version = self._get_system_tool_version(system_tool)
                    if actual_version and not self._version_satisfies(
                        actual_version, dep_version
                    ):
                        if required:
                            return {
                                "success": False,
                                "error": f"系统依赖 {system_tool} 版本不满足 (需要 {dep_version}, 当前 {actual_version})",
                            }
                        else:
                            print(
                                f"[PluginManager] 警告：插件 {plugin_name} 的非必需依赖 {system_tool} 版本不满足"
                            )

            # 检查插件依赖
            elif dep_name.startswith("plugin:"):
                required_plugin = dep_name[7:]  # 去掉 "plugin:" 前缀

                # 检查插件是否已加载
                if not self.is_plugin_loaded(required_plugin):
                    if required:
                        return {
                            "success": False,
                            "error": f"缺少插件依赖：{required_plugin}，请先加载该插件",
                        }
                    else:
                        print(
                            f"[PluginManager] 警告：插件 {plugin_name} 的非必需插件依赖 {required_plugin} 未加载"
                        )
                        continue

                # 检查插件版本
                if dep_version and dep_version != "*":
                    loaded_plugin_info = self.get_plugin_info(required_plugin)
                    if loaded_plugin_info:
                        actual_version = loaded_plugin_info.get("version", "0.0.0")
                        if not self._version_satisfies(actual_version, dep_version):
                            if required:
                                return {
                                    "success": False,
                                    "error": f"插件依赖 {required_plugin} 版本不满足 (需要 {dep_version}, 当前 {actual_version})",
                                }
                            else:
                                print(
                                    f"[PluginManager] 警告：插件 {plugin_name} 的非必需插件依赖 {required_plugin} 版本不满足"
                                )

        return {"success": True, "error": None}

    def _check_system_tool_exists(self, tool_name):
        """
        检查系统工具是否存在

        Args:
            tool_name: 工具名称

        Returns:
            bool: 工具是否存在
        """
        import shutil

        return shutil.which(tool_name) is not None

    def _get_system_tool_version(self, tool_name):
        """
        获取系统工具的版本号

        Args:
            tool_name: 工具名称

        Returns:
            str: 版本号，如果无法获取则返回 None
        """
        import subprocess

        # 尝试常见的版本查询参数
        version_args = [[tool_name, "--version"], [tool_name, "-v"], [tool_name, "-V"]]

        for args in version_args:
            try:
                result = subprocess.run(args, capture_output=True, text=True, timeout=5)

                if result.returncode == 0:
                    # 解析输出，提取版本号
                    output = result.stdout.strip()
                    lines = output.split("\n")

                    for line in lines:
                        # 使用正则表达式匹配版本号
                        match = re.search(r"(\d+\.\d+(?:\.\d+)?)", line)
                        if match:
                            return match.group(1)

                    # 如果没有匹配到，返回第一行
                    if lines:
                        return lines[0]

            except:
                continue

        return None

    def _version_satisfies(self, actual_version, version_requirement):
        """
        检查实际版本是否满足版本要求

        Args:
            actual_version: 实际版本号字符串 (如 "2.1.3")
            version_requirement: 版本要求字符串 (如 ">=2.0", "^3.0.0", "~2.1")

        Returns:
            bool: 是否满足
        """
        try:
            # 解析实际版本号
            actual_parts = [int(x) for x in actual_version.split(".")]

            # 处理不同的版本约束语法
            if version_requirement.startswith(">="):
                required = version_requirement[2:]
                required_parts = [int(x) for x in required.split(".")]
                return self._compare_versions(actual_parts, required_parts) >= 0

            elif version_requirement.startswith("<="):
                required = version_requirement[2:]
                required_parts = [int(x) for x in required.split(".")]
                return self._compare_versions(actual_parts, required_parts) <= 0

            elif version_requirement.startswith(">"):
                required = version_requirement[1:]
                required_parts = [int(x) for x in required.split(".")]
                return self._compare_versions(actual_parts, required_parts) > 0

            elif version_requirement.startswith("<"):
                required = version_requirement[1:]
                required_parts = [int(x) for x in required.split(".")]
                return self._compare_versions(actual_parts, required_parts) < 0

            elif version_requirement.startswith("^"):
                # Caret range: ^1.2.3 允许 1.2.3 到 <2.0.0
                required = version_requirement[1:]
                required_parts = [int(x) for x in required.split(".")]
                return (
                    self._compare_versions(actual_parts, required_parts) >= 0
                    and actual_parts[0] == required_parts[0]
                )

            elif version_requirement.startswith("~"):
                # Tilde range: ~1.2.3 允许 1.2.3 到 <1.3.0
                required = version_requirement[1:]
                required_parts = [int(x) for x in required.split(".")]
                return (
                    self._compare_versions(actual_parts, required_parts) >= 0
                    and actual_parts[0] == required_parts[0]
                    and actual_parts[1] == required_parts[1]
                )

            else:
                # 精确匹配
                required_parts = [int(x) for x in version_requirement.split(".")]
                return actual_parts == required_parts

        except:
            # 解析失败时，尝试简单比较
            try:
                return float(actual_version) >= float(
                    version_requirement.lstrip("<>=^~")
                )
            except:
                return actual_version == version_requirement

    def _compare_versions(self, v1, v2):
        """
        比较两个版本号

        Args:
            v1: 版本号 1（列表形式，如 [2, 1, 3]）
            v2: 版本号 2（列表形式）

        Returns:
            int: -1 (v1 < v2), 0 (v1 == v2), 1 (v1 > v2)
        """
        # 补齐较短的版本号
        max_len = max(len(v1), len(v2))
        v1.extend([0] * (max_len - len(v1)))
        v2.extend([0] * (max_len - len(v2)))

        # 逐位比较
        for i in range(max_len):
            if v1[i] < v2[i]:
                return -1
            elif v1[i] > v2[i]:
                return 1

        return 0

    def register_method(
        self,
        namespace: str,
        method_name: str,
        func: "Callable",
        extra_data: Optional["MethodExtraData"] = None,
    ):
        """
        注册方法到全局域

        Args:
            namespace: 命名空间（通常为插件名）
            method_name: 方法名称
            func: 方法对象
            extra_data: 额外数据配置（可选），如果提供会覆盖 plugin.json 中的配置

        示例：
            plugin_manager.register_method("quick_notes", "create_note", create_note_func)
            调用：plugin_manager.get_method("quick_notes.create_note")
        """
        if namespace not in self.methods_registry:
            self.methods_registry[namespace] = {}

        # 存储方法及其元数据
        self.methods_registry[namespace][method_name] = {
            "func": func,
            "extra_data": extra_data,  # 可选，用于覆盖 json 配置
        }
        
        print(f"[PluginManager] 注册方法：{namespace}.{method_name}")

    def get_method(self, full_name) -> Optional["Callable"]:
        """
        获取已注册的方法

        Args:
            full_name: 完整方法名（格式："namespace.method_name"）

        Returns:
            function: 方法对象，不存在则返回 None

        示例：
            create_note = plugin_manager.get_method("quick_notes.create_note")
        """
        parts = full_name.split(".", 1)
        if len(parts) != 2:
            print(f"[PluginManager] 无效的方法名：{full_name}")
            return None

        namespace, method_name = parts

        if namespace not in self.methods_registry:
            print(f"[PluginManager] 未找到命名空间：{namespace}")
            return None

        if method_name not in self.methods_registry[namespace]:
            print(f"[PluginManager] 未找到方法：{namespace}.{method_name}")
            return None

        method_entry = self.methods_registry[namespace][method_name]
        
        # 兼容旧版本（直接是函数对象）
        if callable(method_entry):
            return method_entry
        
        # 新版本返回字典中的 func
        return method_entry.get("func")

    def get_method_extra_data(self, full_name) -> Optional["MethodExtraData"]:
        """
        获取方法的额外数据配置
        优先从 plugin.json 中读取，如果 register_method 时提供了 extra_data 则覆盖

        Args:
            full_name: 完整方法名（格式："namespace.method_name"）

        Returns:
            MethodExtraData: 额外数据配置，不存在则返回 None

        示例：
            extra_data = plugin_manager.get_method_extra_data("quick_notes.create_note")
            if extra_data and extra_data.get("enable_mcp"):
                # 启用 MCP 功能
                pass
        """
        parts = full_name.split(".", 1)
        if len(parts) != 2:
            return None

        namespace, method_name = parts

        if namespace not in self.methods_registry:
            return None

        if method_name not in self.methods_registry[namespace]:
            return None

        method_entry = self.methods_registry[namespace][method_name]
        
        # 兼容旧版本
        if callable(method_entry):
            return {}
        
        # 优先使用 register_method 时提供的 extra_data（如果有）
        if method_entry.get("extra_data") is not None:
            return method_entry.get("extra_data")
        
        # 否则从 metadata cache 中读取
        if namespace in self.methods_metadata_cache:
            if method_name in self.methods_metadata_cache[namespace]:
                method_info = self.methods_metadata_cache[namespace][method_name]
                return method_info.get("extra_data", {})
        
        return {}

    def get_method_info(self, full_name) -> Optional[dict]:
        """
        获取方法的完整信息（包括函数和额外数据）

        Args:
            full_name: 完整方法名（格式："namespace.method_name"）

        Returns:
            dict: 方法信息字典，包含 func 和 extra_data，不存在则返回 None
        """
        parts = full_name.split(".", 1)
        if len(parts) != 2:
            return None

        namespace, method_name = parts

        if namespace not in self.methods_registry:
            return None

        if method_name not in self.methods_registry[namespace]:
            return None

        method_entry = self.methods_registry[namespace][method_name]
        
        # 兼容旧版本
        if callable(method_entry):
            return {"func": method_entry, "extra_data": {}}
        
        return method_entry

    def add_plugin_tab(self, plugin_name, tab_name, tab_instance, position=None):
        """
        添加插件标签页

        Args:
            plugin_name: 插件名称
            tab_name: 标签页显示名称
            tab_instance: 标签页实例 (QWidget 子类)
            position: 插入位置（可选，从 0 开始）
        """
        tab_info = {
            "plugin_name": plugin_name,
            "name": tab_name,
            "instance": tab_instance,
            "position": position,
        }

        # 如果 notebook 已经初始化，直接添加
        if self.notebook is not None:
            try:
                if position is not None:
                    self.notebook.insertTab(position, tab_instance, tab_name)
                else:
                    self.notebook.addTab(tab_instance, tab_name)
                print(
                    f"[PluginManager] 已添加插件标签页：{tab_name} (插件：{plugin_name})"
                )
            except Exception as e:
                print(f"[PluginManager] 添加标签页失败：{tab_name}, 错误：{e}")
                self.pending_tabs.append(tab_info)
        else:
            # 否则加入待处理列表
            self.pending_tabs.append(tab_info)
            print(
                f"[PluginManager] notebook 未初始化，标签页 {tab_name} 已加入待处理队列"
            )

    def add_plugin_menu(self, plugin_name, menu_name, menu_items):
        """
        添加插件菜单栏

        Args:
            plugin_name: 插件名称
            menu_name: 菜单名称
            menu_items: 菜单项列表，格式：
                       [{"text": "菜单项", "callback": func, "shortcut": "Ctrl+X"}, ...]
        """
        if self.menu_bar is None:
            print(f"[PluginManager] 菜单栏未初始化，无法添加菜单：{menu_name}")
            return

        try:
            from PySide6.QtWidgets import QMenu
            from PySide6.QtGui import QAction

            # 创建菜单
            menu = self.menu_bar.addMenu(menu_name)

            # 添加菜单项
            for item in menu_items:
                action = QAction(item["text"], self.main_window)

                if "shortcut" in item:
                    action.setShortcut(item["shortcut"])

                if "callback" in item and item["callback"]:
                    action.triggered.connect(item["callback"])

                menu.addAction(action)

            print(f"[PluginManager] 已添加插件菜单：{menu_name} (插件：{plugin_name})")

        except Exception as e:
            print(f"[PluginManager] 添加菜单失败：{menu_name}, 错误：{e}")

    def add_text_processing_action_menu(self, plugin_name, menu_name, menu_items):
        """
        添加文本处理功能菜单栏，添加到文本处理组件的标签页
        """

    def is_plugin_loaded(self, plugin_name):
        """检查插件是否已加载"""
        return plugin_name in self.loaded_plugins

    def get_plugin_info(self, plugin_name):
        """获取插件信息"""
        return self.loaded_plugins.get(plugin_name)

    def get_all_methods(self, include_extra_data: bool = False):
        """
        获取所有已注册方法的列表
        
        Args:
            include_extra_data: 是否包含 extra_data 信息，默认为 False
            
        Returns:
            如果 include_extra_data 为 False，返回方法名列表：["namespace.method1", ...]
            如果 include_extra_data 为 True，返回方法信息列表：[{"name": "namespace.method1", "extra_data": {...}}, ...]
        """
        all_methods = []
        for namespace, methods in self.methods_registry.items():
            for method_name, method_entry in methods.items():
                if include_extra_data:
                    # 兼容旧版本
                    if callable(method_entry):
                        extra_data = {}
                    else:
                        # 优先使用 register_method 时提供的 extra_data
                        if method_entry.get("extra_data") is not None:
                            extra_data = method_entry.get("extra_data")
                        else:
                            # 否则从 metadata cache 中读取
                            if namespace in self.methods_metadata_cache:
                                if method_name in self.methods_metadata_cache[namespace]:
                                    method_info = self.methods_metadata_cache[namespace][method_name]
                                    extra_data = method_info.get("extra_data", {})
                                else:
                                    extra_data = {}
                            else:
                                extra_data = {}
                    
                    all_methods.append({
                        "name": f"{namespace}.{method_name}",
                        "extra_data": extra_data
                    })
                else:
                    all_methods.append(f"{namespace}.{method_name}")
        return all_methods

    def unload_plugin(self, plugin_name):
        """
        卸载插件

        Args:
            plugin_name: 插件名称
        """
        if plugin_name not in self.loaded_plugins:
            print(f"[PluginManager] 插件未加载：{plugin_name}")
            return

        plugin_info = self.loaded_plugins[plugin_name]

        # 调用卸载回调
        if hasattr(plugin_info["module"], "unload_plugin"):
            try:
                plugin_info["module"].unload_plugin(self)
            except Exception as e:
                print(f"[PluginManager] 卸载插件失败：{plugin_name}, 错误：{e}")

        # 清理注册的方法
        if plugin_name in self.methods_registry:
            del self.methods_registry[plugin_name]

        # 移除标签页（TODO: 需要实现）
        # 移除菜单（TODO: 需要实现）

        # 从已加载列表中移除
        del self.loaded_plugins[plugin_name]

        print(f"[PluginManager] 插件 {plugin_name} 已卸载")


# 便捷的单例访问函数
def get_plugin_manager():
    """获取插件管理器单例"""
    return PluginManager.get_instance()
