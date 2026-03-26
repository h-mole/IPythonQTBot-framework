#!/usr/bin/env python3
"""
插件调用分析器
使用 Pylint 的 AST 解析功能分析代码中的 plugin_manager 调用模式

功能：
1. 通过类型解析识别 PluginManager 实例
2. 追踪 PluginManager 变量的方法调用
3. 支持多种获取 PluginManager 的方式：
   - 函数参数类型注解: def func(pm: PluginManager)
   - 变量类型注解: pm: PluginManager = xxx
   - 通过 get_plugin_manager() 获取: pm = get_plugin_manager()
4. 提取工具/插件回调清单
5. 支持 JSON 输出和人类可读格式
6. 对变量/表达式参数发出警告
"""

import ast
import json
import sys
from pathlib import Path
from typing import Optional, Union
from dataclasses import dataclass, field, asdict
from enum import Enum


class CallType(Enum):
    """调用类型"""
    GET_METHOD = "get_method"
    REGISTER_METHOD = "register_method"
    GET_METHOD_METADATA = "get_method_metadata"
    GET_METHOD_EXTRA_DATA = "get_method_extra_data"
    GET_METHOD_INFO = "get_method_info"
    REGISTER_SYSTEM_METHOD = "_register_system_method"
    OTHER = "other"


@dataclass
class MethodCall:
    """方法调用信息"""
    call_type: CallType
    method_name: Optional[str]  # 解析出的方法名（如果是字符串字面量）
    namespace: Optional[str]  # 命名空间（从 full_name 解析）
    method_short_name: Optional[str]  # 短方法名
    line_number: int
    column: int
    source_file: str
    raw_argument: str  # 原始参数表达式
    is_resolved: bool  # 是否成功解析为字符串字面量
    variable_name: str  # PluginManager 实例的变量名
    warnings: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "call_type": self.call_type.value,
            "method_name": self.method_name,
            "namespace": self.namespace,
            "method_short_name": self.method_short_name,
            "line_number": self.line_number,
            "column": self.column,
            "source_file": self.source_file,
            "raw_argument": self.raw_argument,
            "is_resolved": self.is_resolved,
            "variable_name": self.variable_name,
            "warnings": self.warnings,
        }


@dataclass
class FileAnalysisResult:
    """单个文件的分析结果"""
    file_path: str
    calls: list[MethodCall] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "file_path": self.file_path,
            "calls": [call.to_dict() for call in self.calls],
            "errors": self.errors,
        }


class PluginManagerTypeTracker:
    """
    追踪 PluginManager 类型的变量
    支持：
    1. 函数参数类型注解: def func(pm: PluginManager)
    2. 变量类型注解: pm: PluginManager = xxx
    3. 通过 get_plugin_manager() 获取: pm = get_plugin_manager()
    """
    
    PLUGIN_MANAGER_NAMES = {"PluginManager", "plugin_manager.PluginManager", 
                            "app_qt.plugin_manager.PluginManager"}
    
    def __init__(self):
        # 在当前作用域中已知的 PluginManager 变量名
        self.pm_variables: set[str] = set()
        # 作用域栈，用于处理嵌套作用域
        self.scope_stack: list[set[str]] = []
    
    def enter_scope(self):
        """进入新作用域"""
        self.scope_stack.append(set())
    
    def exit_scope(self):
        """退出当前作用域"""
        if self.scope_stack:
            self.scope_stack.pop()
    
    def add_pm_variable(self, name: str):
        """添加一个 PluginManager 变量"""
        self.pm_variables.add(name)
        if self.scope_stack:
            self.scope_stack[-1].add(name)
    
    def is_pm_variable(self, name: str) -> bool:
        """检查变量名是否是 PluginManager 实例"""
        return name in self.pm_variables
    
    def is_pm_attribute(self, node: ast.Attribute) -> bool:
        """检查属性访问是否是 PluginManager 实例
        
        处理以下情况:
        - self.pm (pm 被识别为 PluginManager)
        - cls.plugin_manager (plugin_manager 被识别为 PluginManager)
        """
        # 获取完整属性名，如 "self.pm"
        if isinstance(node.value, ast.Name):
            base_name = node.value.id
            full_name = f"{base_name}.{node.attr}"
            # 检查完整名称是否在追踪中
            if full_name in self.pm_variables:
                return True
            # 检查属性名本身是否在追踪中（类级别属性）
            if node.attr in self.pm_variables:
                return True
        
        # 处理嵌套属性访问，如 self.plugin_manager.xxx
        if isinstance(node.value, ast.Attribute):
            # 递归检查基础部分
            if self.is_pm_attribute(node.value):
                return True
        
        return False
    
    def get_pm_attribute_name(self, node: ast.Attribute) -> str:
        """获取 PluginManager 属性的完整名称"""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    
    def check_type_annotation(self, annotation) -> bool:
        """检查类型注解是否是 PluginManager 或 Optional[PluginManager]"""
        if annotation is None:
            return False
        
        # 处理直接名称: PluginManager
        if isinstance(annotation, ast.Name):
            return annotation.id in self.PLUGIN_MANAGER_NAMES or annotation.id == "PluginManager"
        
        # 处理属性访问: plugin_manager.PluginManager
        if isinstance(annotation, ast.Attribute):
            full_name = self._get_attribute_full_name(annotation)
            return full_name in self.PLUGIN_MANAGER_NAMES or full_name.endswith("PluginManager")
        
        # 处理 Optional[PluginManager] 或 Union[PluginManager, None]
        # 这通常是 Subscript 类型，如 Optional[PluginManager]
        if isinstance(annotation, ast.Subscript):
            # 检查是否是 Optional
            if isinstance(annotation.value, ast.Name):
                if annotation.value.id in ("Optional", "Union"):
                    # 检查切片部分是否包含 PluginManager
                    if self._check_subscript_for_pm(annotation.slice):
                        return True
            # 处理 attribute 形式的 Optional，如 typing.Optional
            if isinstance(annotation.value, ast.Attribute):
                if annotation.value.attr in ("Optional", "Union"):
                    if self._check_subscript_for_pm(annotation.slice):
                        return True
        
        return False
    
    def _check_subscript_for_pm(self, slice_node) -> bool:
        """检查 Subscript 的切片部分是否包含 PluginManager"""
        # 处理单个类型: Optional[PluginManager]
        if isinstance(slice_node, ast.Name):
            return slice_node.id in self.PLUGIN_MANAGER_NAMES or slice_node.id == "PluginManager"
        
        # 处理属性访问: Optional[plugin_manager.PluginManager]
        if isinstance(slice_node, ast.Attribute):
            full_name = self._get_attribute_full_name(slice_node)
            return full_name in self.PLUGIN_MANAGER_NAMES or full_name.endswith("PluginManager")
        
        # 处理元组: Union[PluginManager, None] 或 Optional[PluginManager]
        # Python 3.8+ 使用 ast.Tuple，Python 3.9+ 可能不同
        if isinstance(slice_node, ast.Tuple):
            for elt in slice_node.elts:
                if isinstance(elt, ast.Name) and (elt.id in self.PLUGIN_MANAGER_NAMES or elt.id == "PluginManager"):
                    return True
                if isinstance(elt, ast.Attribute):
                    full_name = self._get_attribute_full_name(elt)
                    if full_name in self.PLUGIN_MANAGER_NAMES or full_name.endswith("PluginManager"):
                        return True
        
        # Python 3.10+ 的处理方式可能不同，尝试直接检查字符串表示
        try:
            # 尝试获取源代码片段
            slice_str = ast.unparse(slice_node) if hasattr(ast, 'unparse') else ""
            if "PluginManager" in slice_str:
                return True
        except:
            pass
        
        return False
    
    def _get_attribute_full_name(self, node: ast.Attribute) -> str:
        """获取属性访问的完整名称"""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    
    def is_get_plugin_manager_call(self, node: ast.AST) -> bool:
        """检查是否是 get_plugin_manager() 调用"""
        if isinstance(node, ast.Call):
            func = node.func
            # 直接调用: get_plugin_manager()
            if isinstance(func, ast.Name) and func.id == "get_plugin_manager":
                return True
            # 属性访问: plugin_manager.get_plugin_manager()
            if isinstance(func, ast.Attribute) and func.attr == "get_plugin_manager":
                return True
        return False


class PluginManagerCallVisitor(ast.NodeVisitor):
    """AST 访问者：查找 plugin_manager 相关调用"""
    
    # 需要追踪的方法名
    TRACKED_METHODS = {
        "get_method": CallType.GET_METHOD,
        "register_method": CallType.REGISTER_METHOD,
        "get_method_metadata": CallType.GET_METHOD_METADATA,
        "get_method_extra_data": CallType.GET_METHOD_EXTRA_DATA,
        "get_method_info": CallType.GET_METHOD_INFO,
        "_register_system_method": CallType.REGISTER_SYSTEM_METHOD,
    }
    
    def __init__(self, source_file: str, source_code: str):
        self.source_file = source_file
        self.source_code = source_code
        self.calls: list[MethodCall] = []
        self.errors: list[str] = []
        self.lines = source_code.split('\n')
        self.tracker = PluginManagerTypeTracker()
        
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """访问函数定义，检查参数类型注解"""
        self.tracker.enter_scope()
        
        # 检查函数参数的类型注解
        for arg in node.args.args:
            if self.tracker.check_type_annotation(arg.annotation):
                self.tracker.add_pm_variable(arg.arg)
        
        # 检查 *args 和 **kwargs
        if node.args.vararg and self.tracker.check_type_annotation(node.args.vararg.annotation):
            self.tracker.add_pm_variable(node.args.vararg.arg)
        if node.args.kwarg and self.tracker.check_type_annotation(node.args.kwarg.annotation):
            self.tracker.add_pm_variable(node.args.kwarg.arg)
        
        # 继续遍历函数体
        self.generic_visit(node)
        
        self.tracker.exit_scope()
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """访问异步函数定义"""
        self.visit_FunctionDef(node)  # 复用相同的逻辑
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """访问类定义，检查类属性和 __init__ 中的实例属性类型注解"""
        # 首先遍历类体中的所有语句
        for item in node.body:
            # 检查带类型注解的赋值（类属性）
            if isinstance(item, ast.AnnAssign):
                # 检查类级别的属性（不是 self.xxx 形式）
                if isinstance(item.target, ast.Name):
                    if self.tracker.check_type_annotation(item.annotation):
                        self.tracker.add_pm_variable(item.target.id)
            
            # 检查 __init__ 方法中的实例属性
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                self._check_init_method(item)
        
        # 继续遍历类的其他内容
        self.generic_visit(node)
    
    def _check_init_method(self, node: ast.FunctionDef):
        """检查 __init__ 方法中的实例属性类型注解"""
        for stmt in node.body:
            # 检查带类型注解的赋值（如 self.pm: PluginManager = None）
            if isinstance(stmt, ast.AnnAssign):
                if isinstance(stmt.target, ast.Attribute):
                    if isinstance(stmt.target.value, ast.Name) and stmt.target.value.id == "self":
                        # 检查类型注解是否是 PluginManager
                        if self.tracker.check_type_annotation(stmt.annotation):
                            # 将 self.plugin_manager 添加到追踪
                            attr_name = f"self.{stmt.target.attr}"
                            self.tracker.add_pm_variable(attr_name)
            
            # 检查普通赋值，如 self._plugin_manager = plugin_manager
            elif isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Attribute):
                        if isinstance(target.value, ast.Name) and target.value.id == "self":
                            # 检查右侧是否是 get_plugin_manager() 或 PluginManager 类型
                            if self.tracker.is_get_plugin_manager_call(stmt.value):
                                attr_name = f"self.{target.attr}"
                                self.tracker.add_pm_variable(attr_name)
                            # 检查是否是 PluginManager.get_instance()
                            elif isinstance(stmt.value, ast.Call):
                                func = stmt.value.func
                                if isinstance(func, ast.Attribute) and func.attr == "get_instance":
                                    if isinstance(func.value, ast.Name) and func.value.id == "PluginManager":
                                        attr_name = f"self.{target.attr}"
                                        self.tracker.add_pm_variable(attr_name)
    
    def visit_AnnAssign(self, node: ast.AnnAssign):
        """访问带类型注解的赋值语句"""
        # 检查是否是 PluginManager 类型注解
        if self.tracker.check_type_annotation(node.annotation):
            if isinstance(node.target, ast.Name):
                self.tracker.add_pm_variable(node.target.id)
        
        # 继续遍历
        self.generic_visit(node)
    
    def visit_Assign(self, node: ast.Assign):
        """访问赋值语句，检查是否是 get_plugin_manager() 调用"""
        # 检查右侧是否是 get_plugin_manager() 调用
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id
            
            # 检查是否是 get_plugin_manager() 调用
            if self.tracker.is_get_plugin_manager_call(node.value):
                self.tracker.add_pm_variable(target_name)
            # 检查是否是 PluginManager.get_instance() 调用
            elif isinstance(node.value, ast.Call):
                func = node.value.func
                if isinstance(func, ast.Attribute) and func.attr == "get_instance":
                    # 检查是否是 PluginManager.get_instance()
                    if isinstance(func.value, ast.Name) and func.value.id == "PluginManager":
                        self.tracker.add_pm_variable(target_name)
        
        # 继续遍历
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        """访问函数调用节点"""
        call_info = self._get_call_info(node)
        
        if call_info:
            call_type, variable_name = call_info
            self._process_plugin_manager_call(node, call_type, variable_name)
        
        # 继续遍历子节点
        self.generic_visit(node)
    
    def _get_call_info(self, node: ast.Call) -> Optional[tuple[CallType, str]]:
        """
        判断是否是 PluginManager 的相关调用
        返回 (call_type, variable_name) 或 None
        """
        func = node.func
        
        # 处理属性访问：如 pm.get_method
        if isinstance(func, ast.Attribute):
            method_name = func.attr
            
            if method_name in self.TRACKED_METHODS:
                # 检查调用者是否是已知的 PluginManager 变量
                caller = func.value
                
                if isinstance(caller, ast.Name):
                    var_name = caller.id
                    # 检查是否是已知的 PluginManager 变量，或者是常见的全局名称
                    if self.tracker.is_pm_variable(var_name) or var_name in ("plugin_manager", "pm"):
                        return (self.TRACKED_METHODS[method_name], var_name)
                
                elif isinstance(caller, ast.Attribute):
                    # 处理 self.plugin_manager 或 cls.plugin_manager
                    if isinstance(caller.value, ast.Name):
                        if caller.value.id in ("self", "cls") and caller.attr == "plugin_manager":
                            return (self.TRACKED_METHODS[method_name], f"{caller.value.id}.{caller.attr}")
                        
                        # 处理其他被识别为 PluginManager 类型的属性
                        # 如 self.pm (pm: PluginManager)
                        if self.tracker.is_pm_attribute(caller):
                            attr_name = self.tracker.get_pm_attribute_name(caller)
                            return (self.TRACKED_METHODS[method_name], attr_name)
        
        return None
    
    def _extract_string_value(self, node: ast.AST) -> tuple[Optional[str], bool]:
        """从 AST 节点提取字符串值
        
        Returns:
            (值, 是否成功解析)
        """
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value, True
        return None, False
    
    def _process_plugin_manager_call(self, node: ast.Call, call_type: CallType, variable_name: str):
        """处理 plugin_manager 调用"""
        line_number = node.lineno
        column = node.col_offset
        
        # 获取原始参数文本
        raw_argument = ""
        if node.args:
            raw_argument = self._get_source_segment(node.args[0])
        
        # 解析参数
        method_name = None
        namespace = None
        method_short_name = None
        is_resolved = False
        warnings = []
        
        # 处理不同调用类型的参数
        if call_type == CallType.REGISTER_METHOD:
            # register_method(namespace, method_name, func, ...)
            if len(node.args) >= 2:
                namespace_val, ns_resolved = self._extract_string_value(node.args[0])
                method_val, method_resolved = self._extract_string_value(node.args[1])
                
                if ns_resolved and method_resolved:
                    namespace = namespace_val
                    method_short_name = method_val
                    method_name = f"{namespace}.{method_short_name}"
                    is_resolved = True
                    raw_argument = f'"{namespace}", "{method_short_name}"'
                else:
                    is_resolved = False
                    arg_types = []
                    if not ns_resolved:
                        arg_types.append(f"namespace({type(node.args[0]).__name__})")
                    if not method_resolved:
                        arg_types.append(f"method_name({type(node.args[1]).__name__})")
                    warnings.append(
                        f"WARNING: Line {line_number} register_method uses variable or expression "
                        f"({', '.join(arg_types)}), cannot resolve statically."
                    )
            else:
                warnings.append(f"WARNING: Line {line_number} register_method has insufficient arguments")
                
        elif call_type == CallType.REGISTER_SYSTEM_METHOD:
            # _register_system_method(method_name, func, ...)
            if node.args:
                method_val, method_resolved = self._extract_string_value(node.args[0])
                if method_resolved:
                    namespace = "system"
                    method_short_name = method_val
                    method_name = f"system.{method_short_name}"
                    is_resolved = True
                else:
                    is_resolved = False
                    warnings.append(
                        f"WARNING: Line {line_number} _register_system_method uses variable or expression "
                        f"({type(node.args[0]).__name__}), cannot resolve statically."
                    )
            else:
                warnings.append(f"WARNING: Line {line_number} _register_system_method missing arguments")
        else:
            # 其他方法：get_method, get_method_metadata, get_method_extra_data, get_method_info
            # 这些方法的第一个参数是 full_name (格式: "namespace.method_name")
            if node.args:
                first_arg = node.args[0]
                method_name, is_resolved = self._extract_string_value(first_arg)
                
                if is_resolved and method_name:
                    # 解析命名空间和方法名
                    if '.' in method_name:
                        parts = method_name.split('.', 1)
                        namespace = parts[0]
                        method_short_name = parts[1]
                    else:
                        namespace = None
                        method_short_name = method_name
                else:
                    is_resolved = False
                    arg_type = type(first_arg).__name__
                    warnings.append(
                        f"WARNING: Line {line_number} method call uses variable or expression "
                        f"({arg_type}), cannot resolve statically. Raw argument: {raw_argument}"
                    )
            else:
                warnings.append(f"WARNING: Line {line_number} call missing arguments")
        
        call = MethodCall(
            call_type=call_type,
            method_name=method_name,
            namespace=namespace,
            method_short_name=method_short_name,
            line_number=line_number,
            column=column,
            source_file=self.source_file,
            raw_argument=raw_argument,
            is_resolved=is_resolved,
            variable_name=variable_name,
            warnings=warnings,
        )
        self.calls.append(call)
    
    def _get_source_segment(self, node: ast.AST) -> str:
        """获取节点的源代码文本"""
        try:
            # 尝试使用 ast 模块的 get_source_segment (Python 3.8+)
            segment = ast.get_source_segment(self.source_code, node)
            if segment:
                return segment
        except (AttributeError, TypeError):
            pass
        
        # 回退方案：使用行号和列号提取
        try:
            lineno = getattr(node, 'lineno', 0)
            col_offset = getattr(node, 'col_offset', 0)
            end_lineno = getattr(node, 'end_lineno', lineno)
            end_col_offset = getattr(node, 'end_col_offset', None)
            
            if lineno == 0:
                return ""
            
            if lineno == end_lineno:
                line = self.lines[lineno - 1] if lineno <= len(self.lines) else ""
                if end_col_offset is not None:
                    return line[col_offset:end_col_offset]
                else:
                    return line[col_offset:]
            else:
                # 多行表达式
                result = []
                for i in range(lineno - 1, min(end_lineno, len(self.lines))):
                    if i == lineno - 1:
                        result.append(self.lines[i][col_offset:])
                    elif i == end_lineno - 1:
                        if end_col_offset is not None:
                            result.append(self.lines[i][:end_col_offset])
                        else:
                            result.append(self.lines[i])
                    else:
                        result.append(self.lines[i])
                return '\n'.join(result)
        except Exception:
            return ""


class PluginCallAnalyzer:
    """插件调用分析器主类"""
    
    def __init__(self):
        self.results: list[FileAnalysisResult] = []
    
    def analyze_file(self, file_path: Union[str, Path]) -> FileAnalysisResult:
        """分析单个文件"""
        file_path = Path(file_path)
        
        result = FileAnalysisResult(file_path=str(file_path))
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            result.errors.append(f"Cannot read file: {e}")
            return result
        
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            result.errors.append(f"Syntax error: {e}")
            return result
        except Exception as e:
            result.errors.append(f"Parse error: {e}")
            return result
        
        visitor = PluginManagerCallVisitor(str(file_path), source_code)
        visitor.visit(tree)
        
        result.calls = visitor.calls
        result.errors = visitor.errors
        
        return result
    
    def analyze_directory(
        self, 
        directory: Union[str, Path], 
        pattern: str = "*.py",
        exclude_dirs: Optional[set[str]] = None
    ) -> list[FileAnalysisResult]:
        """分析目录下的所有 Python 文件"""
        directory = Path(directory)
        exclude_dirs = exclude_dirs or {'.git', '__pycache__', '.venv', 'venv', 'node_modules', '.pytest_cache', '.mypy_cache'}
        
        results = []
        
        for py_file in directory.rglob(pattern):
            # 检查是否在排除目录中
            if any(excluded in py_file.parts for excluded in exclude_dirs):
                continue
            
            result = self.analyze_file(py_file)
            results.append(result)
        
        self.results = results
        return results
    
    def get_all_resolved_calls(self) -> list[MethodCall]:
        """获取所有已解析的调用"""
        calls = []
        for result in self.results:
            for call in result.calls:
                if call.is_resolved:
                    calls.append(call)
        return calls
    
    def get_unresolved_calls(self) -> list[MethodCall]:
        """获取所有未解析的调用（使用变量或表达式）"""
        calls = []
        for result in self.results:
            for call in result.calls:
                if not call.is_resolved:
                    calls.append(call)
        return calls
    
    def generate_json_report(self) -> str:
        """生成 JSON 格式的报告"""
        report = {
            "summary": {
                "total_files": len(self.results),
                "total_calls": sum(len(r.calls) for r in self.results),
                "resolved_calls": len(self.get_all_resolved_calls()),
                "unresolved_calls": len(self.get_unresolved_calls()),
            },
            "methods_by_namespace": self._group_by_namespace(),
            "all_calls": [
                call.to_dict() 
                for result in self.results 
                for call in result.calls
            ],
            "unresolved_warnings": [
                {
                    "file": call.source_file,
                    "line": call.line_number,
                    "call_type": call.call_type.value,
                    "raw_argument": call.raw_argument,
                    "warning": call.warnings[0] if call.warnings else "Unknown",
                }
                for result in self.results
                for call in result.calls
                if not call.is_resolved and call.warnings
            ],
        }
        return json.dumps(report, indent=2, ensure_ascii=False)
    
    def _group_by_namespace(self) -> dict:
        """按命名空间分组方法"""
        namespaces = {}
        
        for result in self.results:
            for call in result.calls:
                if call.is_resolved and call.namespace:
                    ns = call.namespace
                    if ns not in namespaces:
                        namespaces[ns] = {
                            "methods": {},
                            "register_calls": [],
                            "get_calls": [],
                        }
                    
                    method_info = {
                        "full_name": call.method_name,
                        "short_name": call.method_short_name,
                        "line_number": call.line_number,
                        "source_file": call.source_file,
                    }
                    
                    if call.call_type == CallType.REGISTER_METHOD:
                        namespaces[ns]["register_calls"].append(method_info)
                        namespaces[ns]["methods"][call.method_short_name] = method_info
                    elif call.call_type == CallType.GET_METHOD:
                        namespaces[ns]["get_calls"].append(method_info)
                    elif call.call_type in (
                        CallType.GET_METHOD_METADATA,
                        CallType.GET_METHOD_EXTRA_DATA,
                        CallType.GET_METHOD_INFO,
                    ):
                        key = f"{call.call_type.value}_calls"
                        if key not in namespaces[ns]:
                            namespaces[ns][key] = []
                        namespaces[ns][key].append(method_info)
                elif call.is_resolved and call.call_type == CallType.REGISTER_SYSTEM_METHOD:
                    # 系统方法
                    ns = "system"
                    if ns not in namespaces:
                        namespaces[ns] = {
                            "methods": {},
                            "register_calls": [],
                            "get_calls": [],
                        }
                    method_info = {
                        "full_name": call.method_name,
                        "short_name": call.method_short_name,
                        "line_number": call.line_number,
                        "source_file": call.source_file,
                    }
                    namespaces[ns]["register_calls"].append(method_info)
                    if call.method_short_name:
                        namespaces[ns]["methods"][call.method_short_name] = method_info
        
        return namespaces
    
    def print_human_readable_report(self):
        """打印人类可读的报告，文件路径和行号格式便于点击跳转"""
        print("=" * 80)
        print("Plugin Call Analysis Report")
        print("=" * 80)
        print()
        
        # 总体统计
        total_calls = sum(len(r.calls) for r in self.results)
        resolved = len(self.get_all_resolved_calls())
        unresolved = len(self.get_unresolved_calls())
        
        print("[Summary]")
        print(f"   Files analyzed: {len(self.results)}")
        print(f"   Total calls: {total_calls}")
        print(f"   [OK] Resolved: {resolved}")
        print(f"   [WARN] Unresolved: {unresolved}")
        print()
        
        # 按文件详细输出
        print("=" * 80)
        print("[Detailed Analysis by File]")
        print("=" * 80)
        print()
        
        for result in self.results:
            if not result.calls:
                continue
            
            # 显示可点击的文件路径
            print(f"\n[File] {result.file_path}")
            print("-" * 60)
            
            # 按调用类型分组
            calls_by_type = {}
            for call in result.calls:
                ct = call.call_type.value
                if ct not in calls_by_type:
                    calls_by_type[ct] = []
                calls_by_type[ct].append(call)
            
            for call_type, calls in sorted(calls_by_type.items()):
                print(f"\n  > {call_type} ({len(calls)} calls):")
                
                for call in calls:
                    # 可点击的文件路径格式: path/to/file.py:123
                    location = f"{call.source_file}:{call.line_number}"
                    if call.is_resolved:
                        print(f"     {location}")
                        print(f"       -> {call.method_name} (via {call.variable_name})")
                    else:
                        print(f"     {location}")
                        print(f"       -> [Unresolved] (via {call.variable_name})")
                        for warning in call.warnings:
                            print(f"          [WARN] {warning}")
        
        # 命名空间汇总
        print()
        print("=" * 80)
        print("[Namespace Summary]")
        print("=" * 80)
        print()
        
        namespaces = self._group_by_namespace()
        for ns, data in sorted(namespaces.items()):
            print(f"\n* {ns}")
            if data["methods"]:
                print(f"   Registered methods:")
                for method_name, info in sorted(data["methods"].items()):
                    # 可点击的文件路径格式
                    print(f"      - {method_name}")
                    print(f"        at {info['source_file']}:{info['line_number']}")
            
            if data.get("get_calls"):
                print(f"   Get method calls ({len(data['get_calls'])}):")
                for call in data["get_calls"]:
                    print(f"      - {call['short_name']}")
                    print(f"        at {call['source_file']}:{call['line_number']}")
        
        # 未解析警告
        unresolved_calls = self.get_unresolved_calls()
        if unresolved_calls:
            print()
            print("=" * 80)
            print("[Unresolved Calls - Need Attention]")
            print("=" * 80)
            print()
            
            for call in unresolved_calls:
                # 可点击的文件路径格式
                print(f"\n{call.source_file}:{call.line_number}")
                print(f"   Call type: {call.call_type.value}")
                print(f"   Variable: {call.variable_name}")
                print(f"   Raw argument: {call.raw_argument}")
                for warning in call.warnings:
                    print(f"   [WARN] {warning}")
        
        print()
        print("=" * 80)
        print("Analysis Complete")
        print("=" * 80)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze plugin_manager call patterns in code using type inference",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --directory ./app_qt --json output.json
  %(prog)s --file ./app_qt/ipython_llm_bridge.py --human
  %(prog)s --directory ./plugins --json -

The analyzer tracks PluginManager instances through:
  1. Function parameter type annotations: def func(pm: PluginManager)
  2. Variable type annotations: pm: PluginManager = xxx
  3. get_plugin_manager() calls: pm = get_plugin_manager()
  4. self.plugin_manager attribute access
        """
    )
    
    parser.add_argument(
        "--file", "-f",
        help="Analyze a single Python file"
    )
    parser.add_argument(
        "--directory", "-d",
        help="Analyze all Python files in directory"
    )
    parser.add_argument(
        "--json", "-j",
        metavar="OUTPUT",
        help="Output JSON format report to file (use - for stdout)"
    )
    parser.add_argument(
        "--human", "-H",
        action="store_true",
        help="Output human-readable format report"
    )
    parser.add_argument(
        "--pattern",
        default="*.py",
        help="File matching pattern (default: *.py)"
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=['.git', '__pycache__', '.venv', 'venv', 'node_modules'],
        help="Directories to exclude"
    )
    
    args = parser.parse_args()
    
    if not args.file and not args.directory:
        parser.error("Please specify --file or --directory")
    
    analyzer = PluginCallAnalyzer()
    
    if args.file:
        result = analyzer.analyze_file(args.file)
        analyzer.results = [result]
    else:
        analyzer.analyze_directory(
            args.directory,
            pattern=args.pattern,
            exclude_dirs=set(args.exclude)
        )
    
    # 输出报告
    if args.json:
        json_report = analyzer.generate_json_report()
        if args.json == "-":
            print(json_report)
        else:
            with open(args.json, 'w', encoding='utf-8') as f:
                f.write(json_report)
            print(f"JSON report saved to: {args.json}")
    
    if args.human or not args.json:
        analyzer.print_human_readable_report()


if __name__ == "__main__":
    main()
