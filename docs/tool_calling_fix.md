# 工具调用处理修复说明

## 问题描述

在 `ipython_llm_bridge.py` 中，LLM 工具调用功能需要完善：

1. **工具名称格式**：传给 LLM 的工具名称格式为 `call_daily_tasks__get_tasks`（前缀 `call_` + 双下划线分隔命名空间和方法名）
2. **返回值处理**：如果工具返回的不是字符串类型，需要用 `repr()` 转为字符串
3. **参数解析**：工具调用的参数可能是空字符串、JSON 字符串或字典，需要正确解析

## 修改内容

### 1. `StreamingOutputHandler` 类修改

#### 添加 `agent_instance` 参数
```python
def __init__(self, ipython_shell=None, agent_instance=None):
    super().__init__()
    self.is_streaming = False
    self.ipython_shell = ipython_shell
    self.response_queue = queue.Queue()
    self.current_stdout = sys.stdout
    self.agent_instance = agent_instance  # Agent 实例引用
    self.start_timer()
```

#### 实现工具调用处理逻辑
在 `_stream_thread` 方法中添加：

```python
# 如果有工具调用，处理它们
if tool_calls:
    self.response_queue.put("\n\n[系统] 检测到工具调用，正在处理...")
    
    # 解析并执行工具调用
    for tool_call in tool_calls:
        try:
            # 获取工具调用信息
            if hasattr(tool_call, 'id') and tool_call.id:
                tool_call_id = tool_call.id
            else:
                tool_call_id = None
            
            # 获取工具名称和参数
            if hasattr(tool_call, 'function') and tool_call.function:
                function = tool_call.function
                tool_name = function.name if hasattr(function, 'name') else None
                arguments_str = function.arguments if hasattr(function, 'arguments') else '{}'
                
                if not tool_name:
                    continue
                
                self.response_queue.put(f"\n[系统] 调用工具：{tool_name}")
                
                # 解析参数字符串
                try:
                    if arguments_str and isinstance(arguments_str, str):
                        arguments = json.loads(arguments_str)
                    elif isinstance(arguments_str, dict):
                        arguments = arguments_str
                    else:
                        arguments = {}
                except json.JSONDecodeError as e:
                    self.response_queue.put(f"\n[警告] 解析工具参数失败：{e}")
                    arguments = {}
                
                # 执行工具调用 - 通过 Agent 实例
                if self.agent_instance:
                    result = self.agent_instance._execute_tool(tool_name, arguments)
                    
                    # 将结果转换为字符串（如果不是字符串类型）
                    if not isinstance(result, str):
                        result_str = repr(result)
                    else:
                        result_str = result
                    
                    self.response_queue.put(f"\n[系统] 工具 {tool_name} 返回：{result_str}")
                    
                    # TODO: 将工具调用结果添加回消息历史，让 LLM 知道结果
                    # self.messages.append({
                    #     "role": "tool",
                    #     "content": result_str,
                    #     "tool_call_id": tool_call_id
                    # })
                else:
                    self.response_queue.put("\n[错误] Agent 实例未初始化，无法执行工具调用")
                        
        except Exception as e:
            error_msg = f"\n[错误] 执行工具调用失败：{e}"
            self.response_queue.put(error_msg)
            import traceback
            traceback.print_exc()
```

### 2. `Agent` 类修改

#### 更新 `StreamingOutputHandler` 初始化
```python
# 流式输出处理器
self.output_handler = StreamingOutputHandler(ipython_shell=ipython_shell, agent_instance=self)
```

#### 改进 `_execute_tool` 方法
```python
def _execute_tool(self, tool_name: str, arguments: Dict) -> Any:
    """
    执行工具调用
    
    Args:
        tool_name: 工具名称 (如 "call_text_helper__get_text")
        arguments: 参数字典
        
    Returns:
        工具执行结果
    """
    # 解析工具名称，找到对应的方法
    # 例如：call_text_helper__get_text -> text_helper.get_text
    if not tool_name.startswith("call_"):
        raise ValueError(f"无效的工具名称：{tool_name}")
    
    # 移除 "call_" 前缀
    method_full_name = tool_name[5:]  # 去掉 "call_"
    
    # 使用双下划线分割命名空间和方法名
    parts = method_full_name.split("__", 1)
    if len(parts) == 2:
        namespace = parts[0]
        method_name = parts[1]  # 方法名中可能包含点号，不需要替换
        full_name = f"{namespace}.{method_name}"
    else:
        # 如果没有双下划线，尝试用单下划线分割（向后兼容旧版本）
        # 旧版本格式：call_namespace_method_name -> namespace.method.name
        parts = method_full_name.split("_", 1)
        if len(parts) == 2:
            namespace = parts[0]
            method_name = parts[1].replace("_", ".")
            full_name = f"{namespace}.{method_name}"
        else:
            full_name = method_full_name.replace("_", ".")
    
    print(f"[工具调用] 工具名：{tool_name} -> 方法：{full_name}")
    
    # 获取方法
    if not self.plugin_manager:
        raise ValueError("插件管理器未初始化")
    method_func = self.plugin_manager.get_method(full_name)
    if not method_func:
        raise ValueError(f"找不到方法：{full_name}")
    
    # 执行方法
    result = method_func(**arguments)
    return result
```

## 工具名称解析规则

### 新格式（推荐）
- **格式**: `call_{namespace}__{method_name}`
- **示例**: 
  - `call_daily_tasks__get_tasks` → `daily_tasks.get_tasks`
  - `call_text_helper__get_text` → `text_helper.get_text`

### 旧格式（向后兼容）
- **格式**: `call_{namespace}_{method_name_with_underscores}`
- **示例**: 
  - `call_text_helper_get_text` → `text.helper.get.text`

## 返回值处理规则

- **字符串类型**: 直接使用
- **非字符串类型**: 使用 `repr()` 转换为字符串
  - 字典：`{"key": "value"}` → `"{'key': 'value'}"`
  - 列表：`[1, 2, 3]` → `"[1, 2, 3]"`
  - None: `None` → `"None"`

## 参数解析规则

1. **JSON 字符串**: 使用 `json.loads()` 解析
2. **字典**: 直接使用
3. **空字符串或其他**: 返回空字典 `{}`

## 测试

创建测试文件 `demos/test_tool_calling.py` 验证：

1. ✓ 工具名称解析（双下划线和单下划线格式）
2. ✓ 返回值转换（字符串、字典、列表、None）
3. ✓ 参数解析（JSON 字符串、空字符串、字典）

运行测试：
```bash
python demos\test_tool_calling.py
```

## 待完善功能

目前工具调用结果**还未添加回消息历史**，需要在后续实现：

```python
# TODO: 将工具调用结果添加回消息历史，让 LLM 知道结果
self.messages.append({
    "role": "tool",
    "content": result_str,
    "tool_call_id": tool_call_id
})
```

这样 LLM 才能根据工具返回结果继续推理和响应。

## 相关文件

- `app_qt/ipython_llm_bridge.py`: 主要修改文件
- `demos/test_tool_calling.py`: 测试文件
- `app_qt/plugin_manager.py`: 插件管理器（提供方法注册和调用）
