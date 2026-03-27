#!/usr/bin/env python3
"""
文件夹方法分析器
基于 plugin_call_analyzer.py，分析文件夹级别的工具方法依赖和提供关系

功能：
1. 分析单个文件夹，获取该文件夹下所有使用的方法（get_method）或注册的方法
2. 列出该文件夹下的工具依赖于或提供了什么方法
3. 支持分析单个文件夹
4. 支持循环调用分析一个路径下全部文件夹
"""

import ast
import json
import sys
from pathlib import Path
from typing import Optional, Union
from dataclasses import dataclass, field, asdict
from collections import defaultdict

# 尝试导入 networkx，用于生成依赖图
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

# 导入原有的分析器
from plugin_call_analyzer import (
    PluginCallAnalyzer,
    CallType,
    MethodCall,
    FileAnalysisResult,
)


@dataclass
class FolderMethodSummary:
    """单个文件夹的方法汇总信息"""
    folder_path: str
    folder_name: str  # 文件夹名称（用于显示）
    
    # 从 plugin.json 读取的元数据
    plugin_metadata: dict = field(default_factory=dict)  # plugin.json 内容
    namespace: str = ""  # 从 plugin.json 读取的命名空间
    
    # 该文件夹提供的方法（通过 register_method 注册）
    # 结构: {namespace: [{method_name, short_name, file, line, enable_mcp, ...}]}
    provided_methods: dict[str, list[dict]] = field(default_factory=lambda: defaultdict(list))
    
    # 该文件夹依赖的方法（通过 get_method 等获取）
    # 结构: {namespace: [{method_name, short_name, file, line, call_type, target_namespace, target_short_name, ...}]}
    dependent_methods: dict[str, list[dict]] = field(default_factory=lambda: defaultdict(list))
    
    # 系统方法注册
    system_methods: list[dict] = field(default_factory=list)
    
    # 未解析的调用
    unresolved_calls: list[dict] = field(default_factory=list)
    
    # 统计信息
    total_files: int = 0
    total_calls: int = 0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "folder_path": self.folder_path,
            "folder_name": self.folder_name,
            "namespace": self.namespace,
            "provided_methods": dict(self.provided_methods),
            "dependent_methods": dict(self.dependent_methods),
            "system_methods": self.system_methods,
            "unresolved_calls": self.unresolved_calls,
            "total_files": self.total_files,
            "total_calls": self.total_calls,
        }
    
    def get_method_enable_mcp(self, method_short_name: str) -> bool:
        """从 plugin.json 获取方法是否启用 MCP"""
        if not self.plugin_metadata:
            return False
        exports = self.plugin_metadata.get("exports", {})
        methods = exports.get("methods", [])
        for method in methods:
            if method.get("name") == method_short_name:
                extra_data = method.get("extra_data", {})
                return extra_data.get("enable_mcp", False)
        return False


@dataclass
class CrossDependency:
    """跨文件夹依赖关系"""
    source_folder: str
    target_folder: str
    method_name: str
    method_namespace: str
    source_file: str
    line_number: int
    
    def to_dict(self) -> dict:
        return {
            "source_folder": self.source_folder,
            "target_folder": self.target_folder,
            "method_name": self.method_name,
            "method_namespace": self.method_namespace,
            "source_file": self.source_file,
            "line_number": self.line_number,
        }


class FolderMethodAnalyzer:
    """文件夹方法分析器"""
    
    def __init__(self):
        self.folder_summaries: list[FolderMethodSummary] = []
        self.all_provided_methods: dict[str, str] = {}  # method_name -> folder_path
        self.cross_dependencies: list[CrossDependency] = []
    
    def _load_plugin_json(self, folder_path: Path) -> tuple[dict, str]:
        """
        加载 plugin.json 文件
        
        Returns:
            (metadata, namespace) 元组，如果文件不存在则返回 ({}, "")
        """
        plugin_json_path = folder_path / "plugin.json"
        if plugin_json_path.exists():
            try:
                with open(plugin_json_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                exports = metadata.get("exports", {})
                namespace = exports.get("namespace", folder_path.name)
                return metadata, namespace
            except (json.JSONDecodeError, IOError) as e:
                print(f"[WARN] Failed to load plugin.json from {folder_path}: {e}", file=sys.stderr)
        return {}, folder_path.name
    
    def _get_enable_mcp_from_metadata(self, metadata: dict, method_short_name: str) -> bool:
        """从 plugin.json 元数据中获取方法的 enable_mcp 属性"""
        exports = metadata.get("exports", {})
        methods = exports.get("methods", [])
        for method in methods:
            if method.get("name") == method_short_name:
                extra_data = method.get("extra_data", {})
                return extra_data.get("enable_mcp", False)
        return False
    
    def analyze_folder(self, folder_path: Union[str, Path]) -> FolderMethodSummary:
        """
        分析单个文件夹，获取该文件夹提供的方法和依赖的方法
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            FolderMethodSummary: 文件夹方法汇总信息
        """
        folder_path = Path(folder_path).resolve()
        
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        if not folder_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {folder_path}")
        
        # 加载 plugin.json
        plugin_metadata, namespace = self._load_plugin_json(folder_path)
        
        # 使用原有的分析器分析文件夹
        analyzer = PluginCallAnalyzer()
        results = analyzer.analyze_directory(folder_path)
        
        # 过滤掉 test_ 或 example_ 开头的测试文件
        results = [
            r for r in results 
            if not Path(r.file_path).name.startswith(('test_', "example_"))
        ]
        
        # 创建汇总
        summary = FolderMethodSummary(
            folder_path=str(folder_path),
            folder_name=folder_path.name,
            plugin_metadata=plugin_metadata,
            namespace=namespace,
        )
        
        summary.total_files = len(results)
        summary.total_calls = sum(len(r.calls) for r in results)
        
        # 分析方法调用
        for result in results:
            for call in result.calls:
                call_info = {
                    "method_name": call.method_name,
                    "namespace": call.namespace,
                    "short_name": call.method_short_name,
                    "file": call.source_file,
                    "line": call.line_number,
                    "raw_argument": call.raw_argument,
                }
                
                if not call.is_resolved:
                    summary.unresolved_calls.append({
                        **call_info,
                        "call_type": call.call_type.value,
                        "warnings": call.warnings,
                    })
                    continue
                
                if call.call_type == CallType.REGISTER_METHOD:
                    # 提供的方法
                    ns = call.namespace or namespace  # 使用从 plugin.json 读取的 namespace
                    # 添加 enable_mcp 信息
                    enable_mcp = self._get_enable_mcp_from_metadata(
                        plugin_metadata, call.method_short_name or ""
                    )
                    call_info["enable_mcp"] = enable_mcp
                    summary.provided_methods[ns].append(call_info)
                    
                    # 记录到全局提供方法映射
                    if call.method_name:
                        self.all_provided_methods[call.method_name] = str(folder_path)
                        
                elif call.call_type == CallType.REGISTER_SYSTEM_METHOD:
                    # 系统方法
                    # 系统方法也检查 enable_mcp
                    enable_mcp = self._get_enable_mcp_from_metadata(
                        plugin_metadata, call.method_short_name or ""
                    )
                    call_info["enable_mcp"] = enable_mcp
                    summary.system_methods.append(call_info)
                    if call.method_name:
                        self.all_provided_methods[call.method_name] = str(folder_path)
                        
                elif call.call_type in (
                    CallType.GET_METHOD,
                    CallType.GET_METHOD_METADATA,
                    CallType.GET_METHOD_EXTRA_DATA,
                    CallType.GET_METHOD_INFO,
                ):
                    # 依赖的方法
                    # 解析目标方法的命名空间和短名
                    target_ns = call.namespace or "unknown"
                    target_short = call.method_short_name or ""
                    
                    call_info.update({
                        "call_type": call.call_type.value,
                        "target_namespace": target_ns,
                        "target_short_name": target_short,
                        "target_full_name": call.method_name,
                    })
                    summary.dependent_methods[target_ns].append(call_info)
        
        return summary
    
    def analyze_path_folders(
        self, 
        path: Union[str, Path],
        exclude_dirs: Optional[set[str]] = None
    ) -> list[FolderMethodSummary]:
        """
        分析路径下的所有直接子文件夹
        
        Args:
            path: 要分析的路径
            exclude_dirs: 要排除的目录名称集合
            
        Returns:
            list[FolderMethodSummary]: 各文件夹的方法汇总列表
        """
        path = Path(path).resolve()
        exclude_dirs = exclude_dirs or {'.git', '__pycache__', '.venv', 'venv', 
                                        'node_modules', '.pytest_cache', '.mypy_cache',
                                        '.gitnexus', '.claude', '.lingma', '.vscode'}
        
        summaries = []
        self.all_provided_methods.clear()
        
        # 获取所有直接子文件夹
        for item in sorted(path.iterdir()):
            if item.is_dir() and item.name not in exclude_dirs:
                try:
                    summary = self.analyze_folder(item)
                    summaries.append(summary)
                except Exception as e:
                    print(f"[ERROR] Failed to analyze {item}: {e}", file=sys.stderr)
        
        self.folder_summaries = summaries
        
        # 分析跨文件夹依赖
        self._analyze_cross_dependencies()
        
        return summaries
    
    def analyze_project(
        self,
        project_root: Union[str, Path],
        plugins_dir: str = "plugins",
        app_qt_dir: str = "app_qt",
        exclude_dirs: Optional[set[str]] = None
    ) -> list[FolderMethodSummary]:
        """
        分析整个项目，包括 plugins 和 app_qt 目录
        
        - plugins 目录下的文件夹作为插件分析，命名空间从 plugin.json 读取
        - app_qt 目录作为系统内核分析，命名空间为 "system"
        - app_qt 下的子文件夹也作为 system 命名空间的一部分分析
        
        Args:
            project_root: 项目根目录
            plugins_dir: 插件目录名称
            app_qt_dir: 应用程序目录名称
            exclude_dirs: 要排除的目录名称集合
            
        Returns:
            list[FolderMethodSummary]: 各文件夹的方法汇总列表
        """
        project_root = Path(project_root).resolve()
        exclude_dirs = exclude_dirs or {'.git', '__pycache__', '.venv', 'venv', 
                                        'node_modules', '.pytest_cache', '.mypy_cache',
                                        '.gitnexus', '.claude', '.lingma', '.vscode'}
        
        summaries = []
        self.all_provided_methods.clear()
        
        # 1. 分析 plugins 目录
        plugins_path = project_root / plugins_dir
        if plugins_path.exists() and plugins_path.is_dir():
            print(f"[INFO] Analyzing plugins directory: {plugins_path}")
            for item in sorted(plugins_path.iterdir()):
                if item.is_dir() and item.name not in exclude_dirs:
                    try:
                        summary = self.analyze_folder(item)
                        summaries.append(summary)
                    except Exception as e:
                        print(f"[ERROR] Failed to analyze plugin {item}: {e}", file=sys.stderr)
        else:
            print(f"[WARN] Plugins directory not found: {plugins_path}")
        
        # 2. 分析 app_qt 目录作为 system 命名空间
        app_qt_path = project_root / app_qt_dir
        if app_qt_path.exists() and app_qt_path.is_dir():
            print(f"[INFO] Analyzing app_qt directory as system namespace: {app_qt_path}")
            
            # 2.1 首先分析 app_qt 根目录下的 Python 文件（作为 system 核心）
            try:
                summary = self._analyze_system_root(app_qt_path)
                summaries.append(summary)
            except Exception as e:
                print(f"[ERROR] Failed to analyze app_qt root: {e}", file=sys.stderr)
            
            # 2.2 然后分析 app_qt 下的子文件夹
            for item in sorted(app_qt_path.iterdir()):
                if item.is_dir() and item.name not in exclude_dirs:
                    try:
                        summary = self._analyze_system_folder(item)
                        summaries.append(summary)
                    except Exception as e:
                        print(f"[ERROR] Failed to analyze app_qt folder {item}: {e}", file=sys.stderr)
        else:
            print(f"[WARN] App_qt directory not found: {app_qt_path}")
        
        self.folder_summaries = summaries
        
        # 分析跨文件夹依赖
        self._analyze_cross_dependencies()
        
        return summaries
    
    def _analyze_system_root(self, app_qt_path: Union[str, Path]) -> FolderMethodSummary:
        """
        分析 app_qt 根目录下的 Python 文件，作为 system 命名空间
        
        Args:
            app_qt_path: app_qt 目录路径
            
        Returns:
            FolderMethodSummary: 文件夹方法汇总信息
        """
        app_qt_path = Path(app_qt_path).resolve()
        
        if not app_qt_path.exists():
            raise FileNotFoundError(f"Path not found: {app_qt_path}")
        
        if not app_qt_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {app_qt_path}")
        
        # 使用原有的分析器分析目录（包括子目录）
        analyzer = PluginCallAnalyzer()
        all_results = analyzer.analyze_directory(app_qt_path)
        
        # 只保留 app_qt 根目录下的 Python 文件（不包括子文件夹中的文件）
        root_results = [
            r for r in all_results 
            if Path(r.file_path).parent == app_qt_path
            and not Path(r.file_path).name.startswith(('test_', "example_"))
        ]
        
        # 创建汇总，强制使用 "system" 作为命名空间和文件夹名
        # 使用 "system" 作为 folder_name 确保所有 system 方法在图中都归到 system 节点下
        summary = FolderMethodSummary(
            folder_path=str(app_qt_path),
            folder_name="system",
            namespace="system",
        )
        
        summary.total_files = len(root_results)
        summary.total_calls = sum(len(r.calls) for r in root_results)
        
        # 分析方法调用
        for result in root_results:
            for call in result.calls:
                call_info = {
                    "method_name": call.method_name,
                    "namespace": "system",  # 强制使用 system 命名空间
                    "short_name": call.method_short_name,
                    "file": call.source_file,
                    "line": call.line_number,
                    "raw_argument": call.raw_argument,
                }
                
                if not call.is_resolved:
                    summary.unresolved_calls.append({
                        **call_info,
                        "call_type": call.call_type.value,
                        "warnings": call.warnings,
                    })
                    continue
                
                if call.call_type == CallType.REGISTER_METHOD:
                    # 提供的方法，强制使用 system 命名空间
                    method_full_name = call.method_name
                    if method_full_name and not method_full_name.startswith("system."):
                        method_full_name = f"system.{call.method_short_name or method_full_name}"
                    
                    call_info["method_name"] = method_full_name
                    call_info["namespace"] = "system"
                    summary.provided_methods["system"].append(call_info)
                    
                    # 记录到全局提供方法映射
                    if method_full_name:
                        self.all_provided_methods[method_full_name] = str(app_qt_path)
                        
                elif call.call_type == CallType.REGISTER_SYSTEM_METHOD:
                    # 系统方法 - 也当作 system 命名空间的方法处理
                    method_full_name = call.method_name
                    if method_full_name and not method_full_name.startswith("system."):
                        method_full_name = f"system.{call.method_short_name or method_full_name}"
                    
                    call_info["method_name"] = method_full_name
                    call_info["namespace"] = "system"
                    summary.system_methods.append(call_info)
                    
                    # 同时添加到 provided_methods，让依赖图能正确显示
                    summary.provided_methods["system"].append(call_info)
                    
                    if method_full_name:
                        self.all_provided_methods[method_full_name] = str(app_qt_path)
                        
                elif call.call_type in (
                    CallType.GET_METHOD,
                    CallType.GET_METHOD_METADATA,
                    CallType.GET_METHOD_EXTRA_DATA,
                    CallType.GET_METHOD_INFO,
                ):
                    # 依赖的方法
                    target_ns = call.namespace or "unknown"
                    target_short = call.method_short_name or ""
                    
                    call_info.update({
                        "call_type": call.call_type.value,
                        "target_namespace": target_ns,
                        "target_short_name": target_short,
                        "target_full_name": call.method_name,
                    })
                    summary.dependent_methods[target_ns].append(call_info)
        
        return summary
    
    def _analyze_system_folder(self, folder_path: Union[str, Path]) -> FolderMethodSummary:
        """
        分析系统文件夹（app_qt 下的文件夹），所有方法标记为 system 命名空间
        
        Args:
            folder_path: 文件夹路径
            
        Returns:
            FolderMethodSummary: 文件夹方法汇总信息
        """
        folder_path = Path(folder_path).resolve()
        
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        if not folder_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {folder_path}")
        
        # 使用原有的分析器分析文件夹
        analyzer = PluginCallAnalyzer()
        results = analyzer.analyze_directory(folder_path)
        
        # 过滤掉 test_ 或 example_ 开头的测试文件
        results = [
            r for r in results 
            if not Path(r.file_path).name.startswith(('test_', "example_"))
        ]
        
        # 创建汇总，强制使用 "system" 作为命名空间和文件夹名
        # 使用 "system" 作为 folder_name 确保所有 system 方法在图中都归到 system 节点下
        summary = FolderMethodSummary(
            folder_path=str(folder_path),
            folder_name="system",
            namespace="system",
        )
        
        summary.total_files = len(results)
        summary.total_calls = sum(len(r.calls) for r in results)
        
        # 分析方法调用
        for result in results:
            for call in result.calls:
                call_info = {
                    "method_name": call.method_name,
                    "namespace": "system",  # 强制使用 system 命名空间
                    "short_name": call.method_short_name,
                    "file": call.source_file,
                    "line": call.line_number,
                    "raw_argument": call.raw_argument,
                }
                
                if not call.is_resolved:
                    summary.unresolved_calls.append({
                        **call_info,
                        "call_type": call.call_type.value,
                        "warnings": call.warnings,
                    })
                    continue
                
                if call.call_type == CallType.REGISTER_METHOD:
                    # 提供的方法，强制使用 system 命名空间
                    method_full_name = call.method_name
                    if method_full_name and not method_full_name.startswith("system."):
                        method_full_name = f"system.{call.method_short_name or method_full_name}"
                    
                    call_info["method_name"] = method_full_name
                    call_info["namespace"] = "system"
                    summary.provided_methods["system"].append(call_info)
                    
                    # 记录到全局提供方法映射
                    if method_full_name:
                        self.all_provided_methods[method_full_name] = str(folder_path)
                        
                elif call.call_type == CallType.REGISTER_SYSTEM_METHOD:
                    # 系统方法 - 也当作 system 命名空间的方法处理
                    method_full_name = call.method_name
                    if method_full_name and not method_full_name.startswith("system."):
                        method_full_name = f"system.{call.method_short_name or method_full_name}"
                    
                    call_info["method_name"] = method_full_name
                    call_info["namespace"] = "system"
                    summary.system_methods.append(call_info)
                    
                    # 同时添加到 provided_methods，让依赖图能正确显示
                    summary.provided_methods["system"].append(call_info)
                    
                    if method_full_name:
                        self.all_provided_methods[method_full_name] = str(folder_path)
                        
                elif call.call_type in (
                    CallType.GET_METHOD,
                    CallType.GET_METHOD_METADATA,
                    CallType.GET_METHOD_EXTRA_DATA,
                    CallType.GET_METHOD_INFO,
                ):
                    # 依赖的方法
                    target_ns = call.namespace or "unknown"
                    target_short = call.method_short_name or ""
                    
                    call_info.update({
                        "call_type": call.call_type.value,
                        "target_namespace": target_ns,
                        "target_short_name": target_short,
                        "target_full_name": call.method_name,
                    })
                    summary.dependent_methods[target_ns].append(call_info)
        
        return summary
    
    def _analyze_cross_dependencies(self):
        """分析跨文件夹依赖关系"""
        self.cross_dependencies = []
        
        for summary in self.folder_summaries:
            for ns, methods in summary.dependent_methods.items():
                for method in methods:
                    method_name = method.get("method_name")
                    if not method_name:
                        continue
                    
                    # 查找该方法由哪个文件夹提供
                    provider_folder = self.all_provided_methods.get(method_name)
                    if provider_folder and provider_folder != summary.folder_path:
                        self.cross_dependencies.append(CrossDependency(
                            source_folder=summary.folder_path,
                            target_folder=provider_folder,
                            method_name=method_name,
                            method_namespace=ns,
                            source_file=method.get("file", ""),
                            line_number=method.get("line", 0),
                        ))
    
    def generate_json_report(self) -> str:
        """生成 JSON 格式的报告"""
        report = {
            "summary": {
                "total_folders": len(self.folder_summaries),
                "total_provided_methods": len(self.all_provided_methods),
                "total_cross_dependencies": len(self.cross_dependencies),
            },
            "all_provided_methods": self.all_provided_methods,
            "folder_analysis": [s.to_dict() for s in self.folder_summaries],
            "cross_dependencies": [d.to_dict() for d in self.cross_dependencies],
        }
        return json.dumps(report, indent=2, ensure_ascii=False)
    
    def print_human_readable_report(self):
        """打印人类可读的报告"""
        print("=" * 80)
        print("Folder Method Analysis Report")
        print("=" * 80)
        print()
        
        # 总体统计
        print("[Summary]")
        print(f"   Folders analyzed: {len(self.folder_summaries)}")
        print(f"   Total provided methods: {len(self.all_provided_methods)}")
        print(f"   Cross-folder dependencies: {len(self.cross_dependencies)}")
        print()
        
        # 按文件夹详细输出
        print("=" * 80)
        print("[Analysis by Folder]")
        print("=" * 80)
        print()
        
        for summary in self.folder_summaries:
            print(f"\n[Folder] {summary.folder_name}")
            print(f"   Path: {summary.folder_path}")
            print("-" * 60)
            
            # 提供的方法
            if summary.provided_methods:
                print(f"\n   [PROVIDES] {sum(len(m) for m in summary.provided_methods.values())} methods:")
                for ns, methods in sorted(summary.provided_methods.items()):
                    print(f"      Namespace: {ns}")
                    for method in methods:
                        method_name = method.get("method_name", "unknown")
                        file_path = method.get("file", "")
                        line = method.get("line", 0)
                        print(f"         - {method_name}")
                        print(f"           at {file_path}:{line}")
            else:
                print(f"\n   [PROVIDES]: (none)")
            
            # 系统方法
            if summary.system_methods:
                print(f"\n   [SYSTEM] {len(summary.system_methods)} methods:")
                for method in summary.system_methods:
                    method_name = method.get("method_name", "unknown")
                    file_path = method.get("file", "")
                    line = method.get("line", 0)
                    print(f"         - {method_name}")
                    print(f"           at {file_path}:{line}")
            
            # 依赖的方法
            if summary.dependent_methods:
                total_deps = sum(len(m) for m in summary.dependent_methods.values())
                print(f"\n   [DEPENDS] {total_deps} methods:")
                for ns, methods in sorted(summary.dependent_methods.items()):
                    print(f"      Namespace: {ns}")
                    for method in methods:
                        method_name = method.get("method_name", "unknown")
                        call_type = method.get("call_type", "unknown")
                        file_path = method.get("file", "")
                        line = method.get("line", 0)
                        print(f"         - {method_name} ({call_type})")
                        print(f"           at {file_path}:{line}")
            else:
                print(f"\n   [DEPENDS]: (none)")
            
            # 未解析的调用
            if summary.unresolved_calls:
                print(f"\n   [WARN] Unresolved calls ({len(summary.unresolved_calls)}):")
                for call in summary.unresolved_calls[:5]:  # 只显示前5个
                    call_type = call.get("call_type", "unknown")
                    raw_arg = call.get("raw_argument", "")
                    file_path = call.get("file", "")
                    line = call.get("line", 0)
                    print(f"         - {call_type}: {raw_arg}")
                    print(f"           at {file_path}:{line}")
                if len(summary.unresolved_calls) > 5:
                    print(f"         ... and {len(summary.unresolved_calls) - 5} more")
            
            print()
        
        # 跨文件夹依赖
        if self.cross_dependencies:
            print("=" * 80)
            print("[Cross-Folder Dependencies]")
            print("=" * 80)
            print()
            
            # 按源文件夹分组
            deps_by_source = defaultdict(list)
            for dep in self.cross_dependencies:
                deps_by_source[dep.source_folder].append(dep)
            
            for source_folder, deps in sorted(deps_by_source.items()):
                source_name = Path(source_folder).name
                print(f"\n[Folder] {source_name} depends on:")
                
                # 按目标文件夹分组
                deps_by_target = defaultdict(list)
                for dep in deps:
                    deps_by_target[dep.target_folder].append(dep)
                
                for target_folder, target_deps in sorted(deps_by_target.items()):
                    target_name = Path(target_folder).name
                    print(f"   -> {target_name} ({len(target_deps)} methods):")
                    for dep in target_deps:
                        print(f"      - {dep.method_name}")
                        print(f"        at {dep.source_file}:{dep.line_number}")
        
        # 方法清单
        print()
        print("=" * 80)
        print("[All Provided Methods]")
        print("=" * 80)
        print()
        
        # 按文件夹分组
        methods_by_folder = defaultdict(list)
        for method_name, folder_path in self.all_provided_methods.items():
            methods_by_folder[folder_path].append(method_name)
        
        for folder_path, methods in sorted(methods_by_folder.items()):
            folder_name = Path(folder_path).name
            print(f"\n[Folder] {folder_name}:")
            for method_name in sorted(methods):
                print(f"   - {method_name}")
        
        print()
        print("=" * 80)
        print("Analysis Complete")
        print("=" * 80)
    
    def print_summary_table(self):
        """打印简洁的汇总表格"""
        print()
        print("=" * 100)
        print(f"{'Folder':<20} {'Files':>8} {'Provides':>10} {'Depends':>10} {'System':>8}")
        print("-" * 100)
        
        for summary in self.folder_summaries:
            provides = sum(len(m) for m in summary.provided_methods.values())
            depends = sum(len(m) for m in summary.dependent_methods.values())
            system = len(summary.system_methods)
            
            print(f"{summary.folder_name:<20} {summary.total_files:>8} {provides:>10} {depends:>10} {system:>8}")
        
        print("-" * 100)
        
        # 总计
        total_files = sum(s.total_files for s in self.folder_summaries)
        total_provides = sum(sum(len(m) for m in s.provided_methods.values()) for s in self.folder_summaries)
        total_depends = sum(sum(len(m) for m in s.dependent_methods.values()) for s in self.folder_summaries)
        total_system = sum(len(s.system_methods) for s in self.folder_summaries)
        
        print(f"{'TOTAL':<20} {total_files:>8} {total_provides:>10} {total_depends:>10} {total_system:>8}")
        print("=" * 100)

    def generate_dependency_graph(self, include_methods: bool = True,
                                   include_project: bool = True) -> Optional['nx.DiGraph']:
        """
        生成模块依赖图
        
        节点类型：
            - Project节点 (project): 项目主程序入口
            - System节点 (system): 系统方法提供者  
            - 插件节点 (plugin): 文件夹/插件级别
            - 方法节点 (method): namespace.xxx
            - MCP节点 (mcp): 特殊的 MCP 中心节点
        
        边类型：
            - 插件 -> 方法 (深绿色实线，表示提供关系)
            - 插件 -> 方法 (红色实线，表示依赖/调用关系)
            - MCP -> 方法 (橙色虚线，表示该方法支持 MCP)
        
        Args:
            include_methods: 是否包含方法级别的节点（默认True）
            include_project: 是否包含 Project 入口节点（默认True）
            
        Returns:
            nx.DiGraph: 有向图对象，如果 networkx 不可用则返回 None
        """
        if not NETWORKX_AVAILABLE:
            print("[ERROR] networkx is not installed. Please install it with: pip install networkx", file=sys.stderr)
            return None
        
        if not self.folder_summaries:
            print("[WARN] No folder summaries available. Please run analyze_path_folders() first.", file=sys.stderr)
            return None
        
        # 创建有向图
        G = nx.DiGraph()
        
        # 收集全局方法注册表
        # method_full_name -> {plugin_name, enable_mcp, namespace, short_name, ...}
        global_method_registry = {}
        
        # 首先遍历所有插件，收集提供的方法
        for summary in self.folder_summaries:
            plugin_name = summary.folder_name
            
            # 收集普通方法
            for ns, methods in summary.provided_methods.items():
                for method in methods:
                    method_name = method.get("method_name", "")
                    if method_name:
                        global_method_registry[method_name] = {
                            "plugin": plugin_name,
                            "namespace": ns,
                            "short_name": method.get("short_name", ""),
                            "enable_mcp": method.get("enable_mcp", False),
                            "file": method.get("file", ""),
                            "line": method.get("line", 0),
                            "is_system": False,
                        }
            
            # 收集系统方法
            for method in summary.system_methods:
                method_name = method.get("method_name", "")
                if method_name:
                    global_method_registry[method_name] = {
                        "plugin": "system",  # 系统方法归于 system 节点
                        "namespace": "system",
                        "short_name": method.get("short_name", ""),
                        "enable_mcp": method.get("enable_mcp", False),
                        "file": method.get("file", ""),
                        "line": method.get("line", 0),
                        "is_system": True,
                    }
        
        if include_methods:
            # 添加 Project 入口节点
            if include_project:
                G.add_node("project",
                          node_type="project",
                          label="project",
                          shape="box",
                          style="rounded,filled",
                          fillcolor="#E0FFFF",
                          color="#00008B",
                          penwidth=2)
            
            # 添加 System 节点
            has_system_methods = any(
                m.get("is_system") for m in global_method_registry.values()
            )
            if has_system_methods:
                G.add_node("system",
                          node_type="system",
                          label="system",
                          shape="box",
                          style="rounded,filled",
                          fillcolor="#B0C4DE",
                          color="#00008B")
            
            # 添加 MCP 节点
            has_mcp_methods = any(
                m.get("enable_mcp") for m in global_method_registry.values()
            )
            if has_mcp_methods:
                G.add_node("MCP",
                          node_type="mcp",
                          label="MCP",
                          shape="diamond",
                          style="filled",
                          fillcolor="#FFD700",
                          color="#FF8C00",
                          penwidth=2)
            
            # 添加插件节点
            for summary in self.folder_summaries:
                plugin_name = summary.folder_name
                G.add_node(plugin_name,
                          node_type="plugin",
                          label=plugin_name,
                          shape="box",
                          style="rounded,filled",
                          fillcolor="#ADD8E6",
                          color="#00008B")
            
            # 添加方法节点和提供关系边
            for method_name, info in global_method_registry.items():
                plugin_name = info["plugin"]
                short_name = info["short_name"] or (method_name.split(".")[-1] if "." in method_name else method_name)
                
                # 方法节点
                fillcolor = "lightyellow" if not info["is_system"] else "lightcyan"
                G.add_node(method_name,
                          node_type="method",
                          label=short_name,
                          full_name=method_name,
                          shape="ellipse",
                          style="filled",
                          fillcolor=fillcolor,
                          color="#B8860B")
                
                # 插件 -> 方法（提供关系，深绿色）
                G.add_edge(plugin_name, method_name,
                          edge_type="provides",
                          color="#006400",
                          penwidth=1.2)
                
                # MCP -> 方法（虚线，enable_mcp）
                if info.get("enable_mcp") and has_mcp_methods:
                    G.add_edge("MCP", method_name,
                              edge_type="mcp",
                              style="dashed",
                              color="#FFA500",
                              penwidth=1.5,
                              label="enable_mcp")
            
            # 添加依赖关系边（插件 -> 方法）
            for summary in self.folder_summaries:
                source_plugin = summary.folder_name
                
                for dep_ns, methods in summary.dependent_methods.items():
                    for method in methods:
                        target_method_name = method.get("target_full_name") or method.get("method_name", "")
                        
                        if target_method_name in global_method_registry:
                            # 添加依赖边：源插件 -> 目标方法
                            G.add_edge(source_plugin, target_method_name,
                                      edge_type="depends",
                                      color="#DC143C",
                                      penwidth=1.0,
                                      label="uses")
                        else:
                            # 外部依赖（未在分析范围内找到）
                            # 创建外部方法节点
                            if not G.has_node(target_method_name):
                                short_name = method.get("target_short_name") or (target_method_name.split(".")[-1] if "." in target_method_name else target_method_name)
                                G.add_node(target_method_name,
                                          node_type="external_method",
                                          label=short_name,
                                          full_name=target_method_name,
                                          shape="ellipse",
                                          style="dashed,filled",
                                          fillcolor="#D3D3D3",
                                          color="#808080")
                            # 添加依赖边
                            G.add_edge(source_plugin, target_method_name,
                                      edge_type="external_depends",
                                      color="#808080",
                                      style="dashed",
                                      penwidth=0.8)
        else:
            # 简化的插件级别图
            self._generate_plugin_level_graph_v2(G, global_method_registry)
        
        return G
    
    def _generate_plugin_level_graph_v2(self, G: 'nx.DiGraph', 
                                        global_method_registry: dict):
        """生成简化版的插件级别依赖图（新版本）"""
        # 收集插件间依赖
        plugin_deps = defaultdict(set)  # source_plugin -> {target_plugins}
        
        for summary in self.folder_summaries:
            source_plugin = summary.folder_name
            
            for dep_ns, methods in summary.dependent_methods.items():
                for method in methods:
                    target_method_name = method.get("target_full_name") or method.get("method_name", "")
                    target_info = global_method_registry.get(target_method_name)
                    
                    if target_info:
                        target_plugin = target_info["plugin"]
                        if target_plugin != source_plugin:
                            plugin_deps[source_plugin].add(target_plugin)
        
        # 添加插件节点
        all_plugins = set(summary.folder_name for summary in self.folder_summaries)
        all_plugins.update(target_plugin for deps in plugin_deps.values() for target_plugin in deps)
        
        for plugin_name in all_plugins:
            G.add_node(plugin_name,
                      node_type="plugin",
                      label=plugin_name,
                      shape="box",
                      style="rounded,filled",
                      fillcolor="#ADD8E6")
        
        # 添加依赖边
        for source_plugin, target_plugins in plugin_deps.items():
            for target_plugin in target_plugins:
                G.add_edge(source_plugin, target_plugin,
                          edge_type="depends",
                          color="#DC143C")
    
    def _generate_plugin_level_graph(self, G: 'nx.DiGraph', 
                                     folder_to_plugin: dict,
                                     plugin_methods: dict,
                                     method_to_plugin: dict):
        """生成简化版的插件级别依赖图"""
        # 添加插件节点
        for plugin_name in folder_to_plugin.values():
            G.add_node(plugin_name,
                      node_type="plugin",
                      label=plugin_name,
                      shape="box",
                      style="rounded,filled",
                      fillcolor="#ADD8E6")
        
        # 分析插件间的依赖
        for summary in self.folder_summaries:
            source_plugin = summary.folder_name
            
            for dep_ns, methods in summary.dependent_methods.items():
                for method in methods:
                    target_method_name = method.get("method_name", "unknown")
                    target_plugin = method_to_plugin.get(target_method_name)
                    
                    if target_plugin and target_plugin != source_plugin:
                        # 检查边是否已存在
                        if G.has_edge(source_plugin, target_plugin):
                            # 更新边的计数
                            G[source_plugin][target_plugin]["count"] = G[source_plugin][target_plugin].get("count", 0) + 1
                            methods_list = G[source_plugin][target_plugin].get("methods", [])
                            methods_list.append(target_method_name)
                            G[source_plugin][target_plugin]["methods"] = methods_list
                        else:
                            G.add_edge(source_plugin, target_plugin,
                                      edge_type="depends",
                                      count=1,
                                      methods=[target_method_name])
    
    def export_dependency_graph_to_dot(self, output_path: Union[str, Path], 
                                       graph: Optional['nx.DiGraph'] = None,
                                       include_methods: bool = True,
                                       include_project: bool = True) -> bool:
        """
        将依赖图导出为 Graphviz DOT 格式
        
        Args:
            output_path: 输出文件路径
            graph: 预先生成的图对象，如果为 None 则重新生成
            include_methods: 是否包含方法级别的节点
            include_project: 是否包含 project 入口节点
            
        Returns:
            bool: 是否成功导出
        """
        if not NETWORKX_AVAILABLE:
            print("[ERROR] networkx is not installed. Please install it with: pip install networkx", file=sys.stderr)
            return False
        
        # 如果没有提供图，则生成
        if graph is None:
            graph = self.generate_dependency_graph(
                include_methods=include_methods,
                include_project=include_project
            )
            if graph is None:
                return False
        
        # 总是使用手动生成 DOT，因为我们的图结构比较复杂
        return self._export_dot_manual(graph, output_path)
    
    def _export_dot_manual(self, graph: 'nx.DiGraph', output_path: Union[str, Path]) -> bool:
        """
        手动生成 DOT 格式文件（不依赖 pygraphviz 或 pydot）
        
        节点类型：
        - Project节点 (project): box 形状，浅青色，粗边框
        - System节点 (system): box 形状，钢蓝色
        - 插件节点 (plugin): box 形状，浅蓝色
        - 方法节点 (method): ellipse 形状，浅黄色
        - 外部方法节点 (external_method): ellipse 形状，灰色虚线
        - MCP节点 (mcp): diamond 形状，金色
        
        边类型：
        - 提供边 (provides): 深绿色实线，Plugin -> Method
        - 依赖边 (depends): 深红色实线，Plugin -> Method
        - 外部依赖边 (external_depends): 灰色虚线
        - MCP边 (mcp): 橙色虚线，MCP -> Method
        
        Args:
            graph: networkx 图对象
            output_path: 输出文件路径
            
        Returns:
            bool: 是否成功导出
        """
        lines = []
        lines.append("digraph DependencyGraph {")
        lines.append("    // Graph settings")
        lines.append("    rankdir=TB;")
        lines.append("    node [fontname=\"Arial\"];")
        lines.append("    edge [fontname=\"Arial\", fontsize=9];")
        lines.append("")
        
        # 分组节点
        project_nodes = []
        system_nodes = []
        plugin_nodes = []
        method_nodes = []
        external_method_nodes = []
        mcp_nodes = []
        
        for node, attrs in graph.nodes(data=True):
            node_type = attrs.get("node_type", "plugin")
            if node_type == "project":
                project_nodes.append((node, attrs))
            elif node_type == "system":
                system_nodes.append((node, attrs))
            elif node_type == "plugin":
                plugin_nodes.append((node, attrs))
            elif node_type == "method":
                method_nodes.append((node, attrs))
            elif node_type == "external_method":
                external_method_nodes.append((node, attrs))
            elif node_type == "mcp":
                mcp_nodes.append((node, attrs))
        
        # 添加 Project 节点
        if project_nodes:
            lines.append("    // Project Node")
            for node, attrs in project_nodes:
                safe_node = self._dot_safe_id(node)
                label = attrs.get("label", node)
                lines.append(f'    {safe_node} [label="{label}", shape=box, '
                            f'style="rounded,filled", fillcolor="#E0FFFF", '
                            f'color="#00008B", penwidth=2];')
            lines.append("")
        
        # 添加 System 节点
        if system_nodes:
            lines.append("    // System Node")
            for node, attrs in system_nodes:
                safe_node = self._dot_safe_id(node)
                label = attrs.get("label", node)
                lines.append(f'    {safe_node} [label="{label}", shape=box, '
                            f'style="rounded,filled", fillcolor="#B0C4DE", '
                            f'color="#00008B", penwidth=1.5];')
            lines.append("")
        
        # 添加 MCP 节点
        if mcp_nodes:
            lines.append("    // MCP Node")
            for node, attrs in mcp_nodes:
                safe_node = self._dot_safe_id(node)
                label = attrs.get("label", node)
                lines.append(f'    {safe_node} [label="{label}", shape=diamond, '
                            f'style=filled, fillcolor="#FFD700", color="#FF8C00", penwidth=2];')
            lines.append("")
        
        # 添加插件节点
        if plugin_nodes:
            lines.append("    // Plugin Nodes")
            for node, attrs in plugin_nodes:
                safe_node = self._dot_safe_id(node)
                label = attrs.get("label", node)
                # system 节点使用更突出的样式
                if node == "system":
                    lines.append(f'    {safe_node} [label="{label}", shape=box, '
                                f'style="rounded,filled", fillcolor="#483D8B", '
                                f'color="#00008B", penwidth=2, fontcolor="#FFFFFF"];')
                else:
                    lines.append(f'    {safe_node} [label="{label}", shape=box, '
                                f'style="rounded,filled", fillcolor="#ADD8E6", '
                                f'color="#00008B", penwidth=1.5];')
            lines.append("")
        
        # 添加方法节点
        if method_nodes:
            lines.append("    // Method Nodes")
            for node, attrs in method_nodes:
                safe_node = self._dot_safe_id(node)
                label = attrs.get("label", node)
                full_name = attrs.get("full_name", node)
                lines.append(f'    {safe_node} [label="{label}", shape=ellipse, '
                            f'style=filled, fillcolor="#FFFFE0", '
                            f'color="#B8860B", tooltip="{full_name}"];')
            lines.append("")
        
        # 添加外部方法节点
        if external_method_nodes:
            lines.append("    // External Method Nodes")
            for node, attrs in external_method_nodes:
                safe_node = self._dot_safe_id(node)
                label = attrs.get("label", node)
                full_name = attrs.get("full_name", node)
                lines.append(f'    {safe_node} [label="{label}", shape=ellipse, '
                            f'style="dashed,filled", fillcolor="#D3D3D3", '
                            f'color="#808080", tooltip="{full_name}"];')
            lines.append("")
        
        # 添加边，按类型分组
        provides_edges = []
        depends_edges = []
        external_depends_edges = []
        mcp_edges = []
        
        for source, target, attrs in graph.edges(data=True):
            edge_type = attrs.get("edge_type", "depends")
            if edge_type == "provides":
                provides_edges.append((source, target, attrs))
            elif edge_type == "depends":
                depends_edges.append((source, target, attrs))
            elif edge_type == "external_depends":
                external_depends_edges.append((source, target, attrs))
            elif edge_type == "mcp":
                mcp_edges.append((source, target, attrs))
        
        # 提供关系边（Plugin -> Method，深绿色）
        if provides_edges:
            lines.append("    // Provides edges (Plugin -> Method)")
            for source, target, attrs in provides_edges:
                safe_source = self._dot_safe_id(source)
                safe_target = self._dot_safe_id(target)
                lines.append(f'    {safe_source} -> {safe_target} [color="#006400", penwidth=1.2];')
            lines.append("")
        
        # 依赖关系边（Plugin -> Method，深红色）
        if depends_edges:
            lines.append("    // Dependency edges (Plugin -> Method)")
            for source, target, attrs in depends_edges:
                safe_source = self._dot_safe_id(source)
                safe_target = self._dot_safe_id(target)
                lines.append(f'    {safe_source} -> {safe_target} [color="#DC143C", '
                            f'penwidth=1.0, label="uses"];')
            lines.append("")
        
        # 外部依赖边（灰色虚线）
        if external_depends_edges:
            lines.append("    // External dependency edges")
            for source, target, attrs in external_depends_edges:
                safe_source = self._dot_safe_id(source)
                safe_target = self._dot_safe_id(target)
                lines.append(f'    {safe_source} -> {safe_target} [color="#808080", '
                            f'style=dashed, penwidth=0.8];')
            lines.append("")
        
        # MCP 虚线边（MCP -> Method，橙色）
        if mcp_edges:
            lines.append("    // MCP edges (MCP -> Method, dashed)")
            for source, target, attrs in mcp_edges:
                safe_source = self._dot_safe_id(source)
                safe_target = self._dot_safe_id(target)
                lines.append(f'    {safe_source} -> {safe_target} [style=dashed, '
                            f'color="#FFA500", penwidth=1.5, label="enable_mcp", '
                            f'fontcolor="#FF8C00", fontsize=9];')
            lines.append("")
        
        lines.append("}")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            print(f"[INFO] Dependency graph exported to: {output_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to write DOT file: {e}", file=sys.stderr)
            return False

    def _dot_safe_id(self, node_id: str) -> str:
        """
        将节点 ID 转换为 DOT 安全格式
        - 如果包含特殊字符，用双引号包裹
        - 替换或转义特殊字符
        """
        # 检查是否需要引号
        if '.' in node_id or '-' in node_id or ' ' in node_id or node_id[0].isdigit():
            # 转义双引号
            safe = node_id.replace('"', '\\"')
            return f'"{safe}"'
        return node_id
    
    def print_dependency_graph_info(self, graph: Optional['nx.DiGraph'] = None, 
                                     include_methods: bool = True):
        """
        打印依赖图的基本信息
        
        Args:
            graph: 预先生成的图对象，如果为 None 则重新生成
            include_methods: 是否包含方法级别的节点
        """
        if not NETWORKX_AVAILABLE:
            print("[ERROR] networkx is not installed. Please install it with: pip install networkx")
            return
        
        if graph is None:
            graph = self.generate_dependency_graph(include_methods=include_methods)
        
        if graph is None or len(graph.nodes()) == 0:
            print("[INFO] No dependency graph available.")
            return
        
        print()
        print("=" * 80)
        print("Dependency Graph Information")
        print("=" * 80)
        print()
        
        # 按类型统计节点
        project_nodes = []
        system_nodes = []
        plugin_nodes = []
        method_nodes = []
        external_method_nodes = []
        mcp_nodes = []
        
        for node, attrs in graph.nodes(data=True):
            node_type = attrs.get("node_type", "plugin")
            if node_type == "project":
                project_nodes.append(node)
            elif node_type == "system":
                system_nodes.append(node)
            elif node_type == "plugin":
                plugin_nodes.append(node)
            elif node_type == "method":
                method_nodes.append(node)
            elif node_type == "external_method":
                external_method_nodes.append(node)
            elif node_type == "mcp":
                mcp_nodes.append(node)
        
        print(f"Total Nodes: {len(graph.nodes())}")
        if project_nodes:
            print(f"  - Project: {len(project_nodes)}")
        if system_nodes:
            print(f"  - System: {len(system_nodes)}")
        print(f"  - Plugins: {len(plugin_nodes)}")
        print(f"  - Methods: {len(method_nodes)}")
        if external_method_nodes:
            print(f"  - External Methods: {len(external_method_nodes)}")
        if mcp_nodes:
            print(f"  - MCP: {len(mcp_nodes)}")
        print(f"Total Edges: {len(graph.edges())}")
        print()
        
        # Project 节点
        if project_nodes:
            print("[Project Node]")
            for node in sorted(project_nodes):
                print(f"   - {node}")
            print()
        
        # System 节点
        if system_nodes:
            print("[System Node]")
            for node in sorted(system_nodes):
                print(f"   - {node}")
            print()
        
        # 插件节点列表
        if plugin_nodes:
            print("[Plugin Nodes]")
            for node in sorted(plugin_nodes):
                print(f"   - {node}")
            print()
        
        # MCP 节点
        if mcp_nodes:
            print("[MCP Node]")
            for node in sorted(mcp_nodes):
                print(f"   - {node}")
            print()
        
        # 方法节点列表（按命名空间分组）
        if method_nodes:
            print("[Method Nodes by Namespace]")
            methods_by_ns = defaultdict(list)
            for method in method_nodes:
                ns = method.split('.')[0] if '.' in method else 'unknown'
                methods_by_ns[ns].append(method)
            
            for ns in sorted(methods_by_ns.keys()):
                methods = methods_by_ns[ns]
                print(f"   {ns} ({len(methods)} methods):")
                for method in sorted(methods)[:5]:  # 只显示前5个
                    short_name = method.split('.')[-1] if '.' in method else method
                    # 检查是否有 MCP
                    attrs = graph.nodes[method]
                    mcp_mark = " [MCP]" if attrs.get("has_mcp", False) else ""
                    print(f"      - {short_name}{mcp_mark}")
                if len(methods) > 5:
                    print(f"      ... and {len(methods) - 5} more")
            print()
        
        # 边统计
        provides_count = 0
        depends_count = 0
        external_depends_count = 0
        mcp_edge_count = 0
        
        for _, _, attrs in graph.edges(data=True):
            edge_type = attrs.get("edge_type", "depends")
            if edge_type == "provides":
                provides_count += 1
            elif edge_type == "depends":
                depends_count += 1
            elif edge_type == "external_depends":
                external_depends_count += 1
            elif edge_type == "mcp":
                mcp_edge_count += 1
        
        print("[Edge Summary]")
        print(f"   - Provides (Plugin->Method): {provides_count}")
        print(f"   - Depends (Plugin->Method): {depends_count}")
        if external_depends_count:
            print(f"   - External Depends: {external_depends_count}")
        print(f"   - MCP connections: {mcp_edge_count}")
        print()
        
        # 显示插件依赖关系
        if depends_count > 0:
            print("[Plugin Dependencies]")
            for source, target, attrs in sorted(graph.edges(data=True), key=lambda x: (x[0], x[1])):
                if attrs.get("edge_type") == "depends":
                    source_name = source
                    target_name = target.split('.')[-1] if '.' in target else target
                    target_ns = target.split('.')[0] if '.' in target else 'unknown'
                    print(f"   {source_name} -> {target_name} ({target_ns})")
            print()
        
        # 显示 MCP 连接
        if mcp_edge_count > 0:
            print("[MCP Enabled Methods]")
            for source, target, attrs in sorted(graph.edges(data=True), key=lambda x: (x[0], x[1])):
                if attrs.get("edge_type") == "mcp":
                    method_short = target.split('.')[-1] if '.' in target else target
                    print(f"   MCP -> {method_short}")
            print()
        
        print("=" * 80)


def main():
    """主函数 - CLI 入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze method dependencies and provisions at folder level",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 分析单个文件夹
  %(prog)s --folder ./plugins/my_tool
  
  # 分析路径下所有文件夹
  %(prog)s --path ./plugins
  
  # 输出 JSON 格式
  %(prog)s --path ./plugins --json output.json
  
  # 简洁表格输出
  %(prog)s --path ./plugins --table
  
  # 分析 app_qt 目录下所有文件夹
  %(prog)s --path ./app_qt --human
  
  # 导出依赖图到 DOT 格式（包含插件和方法节点）
  %(prog)s --path ./plugins --dot dependency_graph.dot
  
  # 只导出插件级别的依赖图（不包含方法节点）
  %(prog)s --path ./plugins --dot plugin_graph.dot --plugin-only
  
  # 显示依赖图信息并导出
  %(prog)s --path ./plugins --graph-info --dot dependency_graph.dot
  
  # 只显示依赖次数 >= 3 的边（仅插件级别模式）
  %(prog)s --path ./plugins --dot filtered_graph.dot --min-edge-count 3 --plugin-only
  
  # 分析整个项目（plugins + app_qt）并导出依赖图
  %(prog)s --project --dot project_deps.dot
  
  # 分析整个项目（指定项目根目录）
  %(prog)s --project /path/to/project --dot project_deps.dot
  
  # 分析整个项目并显示依赖图信息
  %(prog)s --project --graph-info --dot project_deps.dot
        """
    )
    
    # 分析模式
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--folder", "-f",
        help="Analyze a single folder"
    )
    group.add_argument(
        "--path", "-p",
        help="Analyze all direct subfolders in the path"
    )
    group.add_argument(
        "--project",
        metavar="PROJECT_ROOT",
        nargs="?",
        const=".",
        default=None,
        help="Analyze entire project (plugins + app_qt). Optionally specify project root path (default: current directory)"
    )
    
    # 输出选项
    parser.add_argument(
        "--json", "-j",
        metavar="OUTPUT",
        help="Output JSON format report to file (use - for stdout)"
    )
    parser.add_argument(
        "--human", "-H",
        action="store_true",
        help="Output human-readable format report (default)"
    )
    parser.add_argument(
        "--table", "-t",
        action="store_true",
        help="Output summary table only"
    )
    parser.add_argument(
        "--dot", "-d",
        metavar="OUTPUT",
        help="Export dependency graph to DOT format file (requires networkx)"
    )
    parser.add_argument(
        "--graph-info", "-g",
        action="store_true",
        help="Print dependency graph information"
    )
    parser.add_argument(
        "--plugin-only",
        action="store_true",
        help="In dependency graph, show only plugin-level nodes (no method nodes)"
    )
    parser.add_argument(
        "--no-project",
        action="store_true",
        help="In dependency graph, exclude the project entry node"
    )
    
    # 排除选项
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=['.git', '__pycache__', '.venv', 'venv', 'node_modules',
                '.pytest_cache', '.mypy_cache', '.gitnexus', '.claude', '.lingma'],
        help="Directories to exclude"
    )
    
    # 依赖图选项
    parser.add_argument(
        "--min-edge-count",
        type=int,
        default=1,
        metavar="N",
        help="Filter edges with count less than N in dependency graph"
    )
    
    args = parser.parse_args()
    
    analyzer = FolderMethodAnalyzer()
    
    if args.folder:
        # 分析单个文件夹
        try:
            summary = analyzer.analyze_folder(args.folder)
            analyzer.folder_summaries = [summary]
            
            # 更新提供的方法映射
            for ns, methods in summary.provided_methods.items():
                for method in methods:
                    if method.get("method_name"):
                        analyzer.all_provided_methods[method["method_name"]] = summary.folder_path
            for method in summary.system_methods:
                if method.get("method_name"):
                    analyzer.all_provided_methods[method["method_name"]] = summary.folder_path
                    
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.project:
        # 分析整个项目（plugins + app_qt）
        analyzer.analyze_project(
            args.project,
            exclude_dirs=set(args.exclude)
        )
    else:
        # 分析路径下所有文件夹
        analyzer.analyze_path_folders(args.path, exclude_dirs=set(args.exclude))
    
    # 输出报告
    if args.json:
        json_report = analyzer.generate_json_report()
        if args.json == "-":
            print(json_report)
        else:
            with open(args.json, 'w', encoding='utf-8') as f:
                f.write(json_report)
            print(f"JSON report saved to: {args.json}")
    
    # 生成和导出依赖图
    dependency_graph = None
    include_methods = not args.plugin_only
    include_project = not args.no_project
    
    if args.dot or args.graph_info:
        dependency_graph = analyzer.generate_dependency_graph(
            include_methods=include_methods,
            include_project=include_project
        )
        
        if dependency_graph and args.min_edge_count > 1 and not include_methods:
            # 只在插件级别模式下过滤低权重的边
            edges_to_remove = [(u, v) for u, v, d in dependency_graph.edges(data=True) 
                              if d.get("count", 1) < args.min_edge_count]
            dependency_graph.remove_edges_from(edges_to_remove)
            # 移除孤立节点
            isolated = [n for n in dependency_graph.nodes() if dependency_graph.degree(n) == 0]
            dependency_graph.remove_nodes_from(isolated)
        
        if args.graph_info:
            analyzer.print_dependency_graph_info(dependency_graph, include_methods=include_methods)
        
        if args.dot and dependency_graph:
            success = analyzer.export_dependency_graph_to_dot(
                args.dot, dependency_graph, 
                include_methods=include_methods,
                include_project=include_project
            )
            if not success:
                print("[WARN] Failed to export dependency graph to DOT format.", file=sys.stderr)
    
    if args.table:
        analyzer.print_summary_table()
    elif args.human or not args.json:
        analyzer.print_human_readable_report()


if __name__ == "__main__":
    main()
