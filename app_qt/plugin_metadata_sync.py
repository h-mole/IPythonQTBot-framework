"""
插件元数据同步器

功能：
1. 自动提取代码中的函数签名和文档字符串
2. 对比 plugin.json 中的方法声明
3. 以代码中的实际内容为准，自动更新 plugin.json
4. 检测 plugin.json 中声明了但代码中没有的 extra_data/mcp 配置

使用方法：
    在 PluginManager 加载插件时自动调用
"""

import ast
import inspect
import json
import os
import re
import sys
from typing import Any, Callable, Optional, TypedDict
from dataclasses import dataclass, field, asdict
import logging

try:
    from docstring_parser import parse as parse_docstring_lib
    DOCSTRING_PARSER_AVAILABLE = True
except ImportError:
    DOCSTRING_PARSER_AVAILABLE = False
    parse_docstring_lib = None

logger = logging.getLogger(__name__)


class ParameterInfo(TypedDict, total=False):
    """参数信息结构"""
    name: str
    type: str
    description: str
    required: bool
    default: Any


class ReturnsInfo(TypedDict, total=False):
    """返回值信息结构"""
    type: str
    description: str


class MethodMetadata(TypedDict, total=False):
    """方法元数据结构"""
    name: str
    description: str
    stable: bool
    parameters: list[ParameterInfo]
    returns: ReturnsInfo
    extra_data: dict[str, Any]


@dataclass
class ExtractedMethodInfo:
    """从代码中提取的方法信息"""
    name: str
    description: str = ""
    parameters: list[dict] = field(default_factory=list)
    returns: dict = field(default_factory=dict)
    extra_data: dict = field(default_factory=dict)
    
    def to_plugin_json_format(self) -> dict:
        """转换为 plugin.json 中的方法格式"""
        result = {
            "name": self.name,
            "description": self.description,
            "stable": True,
            "parameters": self.parameters,
            "returns": self.returns,
        }
        if self.extra_data:
            result["extra_data"] = self.extra_data
        return result


def parse_docstring(docstring: str) -> tuple[str, dict[str, str], str]:
    """
    解析文档字符串，提取描述、参数说明和返回类型
    使用 docstring_parser 库（与 ipython_llm_bridge.py 同款）
    
    Args:
        docstring: 函数的文档字符串
        
    Returns:
        (描述, 参数字典, 返回类型)
    """
    if not docstring:
        return "", {}, ""
    
    # 使用 docstring_parser 库解析
    if DOCSTRING_PARSER_AVAILABLE and parse_docstring_lib:
        try:
            parsed = parse_docstring_lib(docstring)
            
            # 提取描述（short + long description）
            description = parsed.short_description or ""
            if parsed.long_description:
                description = (description + "\n" + parsed.long_description).strip()
            
            # 提取参数文档
            param_docs = {}
            if parsed.params:
                for param in parsed.params:
                    param_docs[param.arg_name] = param.description or ""
            
            # 提取返回类型和描述
            return_type = ""
            return_desc = ""
            if parsed.returns:
                if parsed.returns.type_name:
                    return_type = parsed.returns.type_name
                if parsed.returns.description:
                    return_desc = parsed.returns.description
            
            if return_desc:
                param_docs['__returns__'] = return_desc
            
            return description, param_docs, return_type
            
        except Exception:
            # 解析失败时回退到简单解析
            pass
    
    # 回退：简单解析（不使用 docstring_parser）
    lines = docstring.strip().split('\n')
    description_lines = []
    param_docs = {}
    return_type = ""
    
    current_section = "description"
    
    for line in lines:
        stripped = line.strip()
        
        # 检测 Args: 部分
        if stripped == "Args:" or stripped.startswith("Args:"):
            current_section = "args"
            continue
            
        # 检测 Returns: 部分
        if stripped == "Returns:" or stripped.startswith("Returns:"):
            current_section = "returns"
            continue
        
        # 检测 Raises: 部分（跳过）
        if stripped == "Raises:" or stripped.startswith("Raises:"):
            current_section = "raises"
            continue
        
        # 解析参数
        if current_section == "args":
            param_match = re.match(r'(\w+):\s*(.+)', stripped)
            if param_match:
                param_name = param_match.group(1)
                rest = param_match.group(2)
                desc_match = re.split(r'[-:：]\s*', rest, maxsplit=1)
                if len(desc_match) > 1:
                    param_docs[param_name] = desc_match[1].strip()
                else:
                    param_docs[param_name] = rest.strip()
        
        # 解析返回值
        elif current_section == "returns":
            if stripped and not return_type:
                type_match = re.match(r'^([\w\[\]|\s,]+)[:：]\s*(.+)', stripped)
                if type_match:
                    potential_type = type_match.group(1).strip()
                    if re.match(r'^(str|int|float|bool|list|dict|tuple|None|object|any|set|Callable|Union|Optional|\w+)(\[.*\])?$', potential_type, re.IGNORECASE):
                        return_type = potential_type
                        param_docs['__returns__'] = type_match.group(2).strip()
        
        # 解析描述
        elif current_section == "description":
            if stripped:
                description_lines.append(stripped)
    
    description = ' '.join(description_lines)
    return description, param_docs, return_type


def extract_type_hint(type_hint) -> str:
    """
    提取类型提示的字符串表示
    
    Args:
        type_hint: 类型提示对象
        
    Returns:
        类型字符串
    """
    if type_hint is inspect.Parameter.empty:
        return "any"
    
    # 处理常见的类型提示
    type_str = str(type_hint)
    
    # 简化类型表示
    type_mapping = {
        "<class 'str'>": "str",
        "<class 'int'>": "int",
        "<class 'float'>": "float",
        "<class 'bool'>": "bool",
        "<class 'list'>": "list",
        "<class 'dict'>": "dict",
        "<class 'tuple'>": "tuple",
        "<class 'NoneType'>": "None",
    }
    
    for full, short in type_mapping.items():
        type_str = type_str.replace(full, short)
    
    # 处理 Optional[X] -> X 或 Union[X, None]
    type_str = re.sub(r'Optional\[(.+?)\]', r'\1 | None', type_str)
    type_str = re.sub(r'Union\[(.+?),\s*NoneType\]', r'\1 | None', type_str)
    
    # 处理 List[X] -> list
    if 'list[' in type_str.lower() or 'List[' in type_str:
        return "list"
    
    # 处理 Dict[X, Y] -> dict
    if 'dict[' in type_str.lower() or 'Dict[' in type_str:
        return "dict"
    
    return type_str.lower() if type_str in type_mapping.values() else type_str


def extract_method_info_from_function(func: Callable, method_name: str = None) -> ExtractedMethodInfo:
    """
    从函数对象提取方法元数据
    
    Args:
        func: 函数对象
        method_name: 方法名称（如果不提供则使用函数名）
        
    Returns:
        ExtractedMethodInfo 对象
    """
    name = method_name or func.__name__
    
    # 获取签名
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        sig = None
    
    # 解析文档字符串
    docstring = inspect.getdoc(func) or ""
    description, param_docs, doc_return_type = parse_docstring(docstring)
    
    # 提取参数信息
    parameters = []
    if sig:
        for param_name, param in sig.parameters.items():
            # 跳过 self 参数
            if param_name == 'self':
                continue
            
            param_info: ParameterInfo = {
                "name": param_name,
                "type": extract_type_hint(param.annotation),
                "description": param_docs.get(param_name, ""),
                "required": param.default is inspect.Parameter.empty,
            }
            
            # 如果有默认值且不是空值，添加默认值信息
            if param.default is not inspect.Parameter.empty:
                param_info["default"] = param.default
            
            parameters.append(param_info)
    
    # 提取返回值信息
    returns: ReturnsInfo = {
        "type": "any",
        "description": "",
    }
    if sig and sig.return_annotation is not inspect.Signature.empty:
        # 优先使用类型注解
        returns["type"] = extract_type_hint(sig.return_annotation)
        returns["description"] = param_docs.get("__returns__", "")
    elif doc_return_type:
        # 如果没有类型注解，尝试从 docstring 解析
        returns["type"] = doc_return_type.lower()
        returns["description"] = param_docs.get("__returns__", "")
    
    return ExtractedMethodInfo(
        name=name,
        description=description or f"API: {name}",
        parameters=parameters,
        returns=returns,
        extra_data={},
    )


def extract_api_methods_from_module(module) -> dict[str, ExtractedMethodInfo]:
    """
    从模块中提取所有以 _api 结尾的方法
    
    Args:
        module: 模块对象
        
    Returns:
        方法名到 ExtractedMethodInfo 的映射
    """
    methods = {}
    
    for attr_name in dir(module):
        # 查找以 _api 结尾的方法
        if attr_name.endswith('_api'):
            api_name = attr_name[:-4]  # 去掉 _api 后缀
            attr = getattr(module, attr_name)
            
            if callable(attr):
                info = extract_method_info_from_function(attr, api_name)
                methods[api_name] = info
    
    return methods


class PluginMetadataSync:
    """
    插件元数据同步器
    
    负责同步 plugin.json 和实际代码中的方法声明
    """
    
    def __init__(self, plugin_path: str, plugin_config: dict):
        """
        初始化同步器
        
        Args:
            plugin_path: 插件目录路径
            plugin_config: plugin.json 的配置内容
        """
        self.plugin_path = plugin_path
        self.plugin_config = plugin_config
        self.plugin_name = plugin_config.get("name", "unknown")
        self.changes_made = []
        
    def sync_from_code(
        self, 
        registered_methods: dict[str, dict],
        save_to_file: bool = True
    ) -> dict:
        """
        从已注册的方法同步到 plugin.json
        
        Args:
            registered_methods: 已注册的方法字典，格式为 {method_name: {func, extra_data, ...}}
            save_to_file: 是否保存更新后的配置到文件
            
        Returns:
            更新后的 plugin_config
        """
        exports = self.plugin_config.get("exports", {})
        json_methods = exports.get("methods", [])
        
        # 构建 plugin.json 中方法的字典（按名称）
        json_methods_dict = {m["name"]: m for m in json_methods}
        
        # 新的方法列表
        new_methods = []
        
        # 检查每个已注册的方法
        for method_name, reg_info in registered_methods.items():
            func = reg_info.get("func")
            code_extra_data = reg_info.get("extra_data", {})
            
            if func is None:
                continue
            
            # 从代码提取方法信息
            code_info = extract_method_info_from_function(func, method_name)
            
            # 合并代码中的 extra_data（注册时传入的优先）
            if code_extra_data:
                code_info.extra_data = code_extra_data
            
            # 检查 plugin.json 中是否已存在此方法
            if method_name in json_methods_dict:
                json_method = json_methods_dict[method_name]
                
                # 比较并同步
                updated_method = self._merge_method_info(code_info, json_method)
                new_methods.append(updated_method)
                
                # 检测不一致
                self._check_inconsistencies(code_info, json_method, method_name)
            else:
                # 代码中有但 plugin.json 中没有，添加新方法
                new_methods.append(code_info.to_plugin_json_format())
                self.changes_made.append(f"添加新方法: {method_name}")
                logger.info(f"[PluginMetadataSync] 插件 '{self.plugin_name}' 添加新方法: {method_name}")
        
        # 检查 plugin.json 中有但代码中没有的方法（可能是已删除的方法）
        code_method_names = set(registered_methods.keys())
        for json_method in json_methods:
            json_name = json_method.get("name", "")
            if json_name and json_name not in code_method_names:
                # plugin.json 中有但代码中没有，保留但标记为不稳定
                json_method["stable"] = False
                new_methods.append(json_method)
                self.changes_made.append(f"标记为不稳定(代码中不存在): {json_name}")
                logger.warning(
                    f"[PluginMetadataSync] 插件 '{self.plugin_name}' 的方法 '{json_name}' "
                    f"在代码中不存在，已标记为 unstable"
                )
        
        # 更新配置
        exports["methods"] = new_methods
        self.plugin_config["exports"] = exports
        
        # 保存到文件
        if save_to_file and self.changes_made:
            self._save_config()
        
        return self.plugin_config
    
    def _merge_method_info(self, code_info: ExtractedMethodInfo, json_method: dict) -> dict:
        """
        合并代码中提取的信息和 plugin.json 中的信息
        以代码中的内容为准
        
        Args:
            code_info: 从代码提取的信息
            json_method: plugin.json 中的方法声明
            
        Returns:
            合并后的方法信息
        """
        result = json_method.copy()
        
        # 以代码为准更新描述
        if code_info.description and code_info.description != json_method.get("description", ""):
            result["description"] = code_info.description
        
        # 以代码为准更新参数
        if code_info.parameters:
            # 保留原有的参数描述（如果代码中没有提供）
            json_params = {p["name"]: p for p in json_method.get("parameters", [])}
            merged_params = []
            
            for code_param in code_info.parameters:
                param_name = code_param["name"]
                if param_name in json_params:
                    # 合并：使用代码中的类型和必填信息，但保留 json 中的描述（如果代码中没有）
                    json_param = json_params[param_name]
                    merged_param = code_param.copy()
                    if not code_param.get("description") and json_param.get("description"):
                        merged_param["description"] = json_param["description"]
                    merged_params.append(merged_param)
                else:
                    merged_params.append(code_param)
            
            result["parameters"] = merged_params
        
        # 以代码为准更新返回值信息
        if code_info.returns:
            result["returns"] = code_info.returns
        
        # 合并 extra_data（代码中的优先）
        if code_info.extra_data:
            result["extra_data"] = {**json_method.get("extra_data", {}), **code_info.extra_data}
        
        return result
    
    def _check_inconsistencies(
        self, 
        code_info: ExtractedMethodInfo, 
        json_method: dict, 
        method_name: str
    ):
        """
        检测 plugin.json 和代码之间的不一致
        
        Args:
            code_info: 从代码提取的信息
            json_method: plugin.json 中的方法声明
            method_name: 方法名
        """
        # 检查 plugin.json 声明了 MCP 但代码中没有
        json_extra = json_method.get("extra_data", {})
        code_extra = code_info.extra_data
        
        if json_extra.get("enable_mcp") and not code_extra.get("enable_mcp"):
            logger.warning(
                f"[PluginMetadataSync] 插件 '{self.plugin_name}' 的方法 '{method_name}' "
                f"在 plugin.json 中声明了 enable_mcp=true，但代码注册时未提供 extra_data。"
                f"建议在代码中添加: extra_data={{'enable_mcp': True}}"
            )
            self.changes_made.append(
                f"警告: {method_name} 的 MCP 声明在代码中缺失，已自动从代码同步到 JSON"
            )
        
        # 检查参数数量不一致
        json_params = {p["name"] for p in json_method.get("parameters", [])}
        code_params = {p["name"] for p in code_info.parameters}
        
        if json_params != code_params:
            added = code_params - json_params
            removed = json_params - code_params
            if added:
                self.changes_made.append(f"{method_name}: 新增参数 {added}")
            if removed:
                self.changes_made.append(f"{method_name}: 移除参数 {removed}")
    
    def _save_config(self):
        """保存配置到 plugin.json"""
        config_path = os.path.join(self.plugin_path, "plugin.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.plugin_config, f, ensure_ascii=False, indent=2)
            logger.info(
                f"[PluginMetadataSync] 插件 '{self.plugin_name}' 的配置已更新: {config_path}"
            )
        except Exception as e:
            logger.error(f"[PluginMetadataSync] 保存配置失败: {e}")
    
    def get_changes_summary(self) -> str:
        """获取变更摘要"""
        if not self.changes_made:
            return f"插件 '{self.plugin_name}' 无需更新"
        return f"插件 '{self.plugin_name}' 的变更:\n" + "\n".join(f"  - {c}" for c in self.changes_made)


def sync_plugin_metadata(
    plugin_path: str,
    plugin_config: dict,
    registered_methods: dict[str, dict],
    save_to_file: bool = True
) -> tuple[dict, str]:
    """
    同步插件元数据的便捷函数
    
    Args:
        plugin_path: 插件目录路径
        plugin_config: plugin.json 的配置内容
        registered_methods: 已注册的方法字典
        save_to_file: 是否保存更新后的配置到文件
        
    Returns:
        (更新后的配置, 变更摘要)
    """
    sync = PluginMetadataSync(plugin_path, plugin_config)
    updated_config = sync.sync_from_code(registered_methods, save_to_file)
    summary = sync.get_changes_summary()
    return updated_config, summary
