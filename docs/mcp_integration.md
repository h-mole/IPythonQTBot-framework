# MCP 类型解析集成说明

## 概述

已将 `ipython_llm_bridge.py` 中的工具调用机制改为使用 **MCP (Model Context Protocol)** 包的成熟类型解析和签名解析机制，不再重复造轮子。

## 主要改进

### 1. 使用 MCP FastMCP 进行类型解析

**之前的问题：**
- 自己实现类型推断逻辑（`_infer_param_type`）
- 手动处理 Python 类型到 JSON Schema 的映射
- 代码复杂且容易出错

**现在的方案：**
```python
from mcp.server.fastmcp import FastMCP

# 创建临时 FastMCP 实例用于类型解析
temp_mcp = FastMCP("temp")

# 使用 MCP 的内部机制解析函数签名和类型
tool_decorator = temp_mcp.tool()(method_func)
```

### 2. 类型映射机制

MCP 使用的类型映射（基于 Pydantic）：

| Python 类型 | OpenAI/MCP 类型 |
|------------|----------------|
| `int`      | `integer`      |
| `float`    | `number`       |
| `bool`     | `boolean`      |
| `str`      | `string`       |
| `list`     | `array`        |
| `dict`     | `object`       |
| `List[T]`  | `array`        |
| `Dict[K,V]`| `object`       |

### 3. 自动文档字符串提取

利用 MCP 的文档解析机制，自动从函数的 docstring 中提取：
- 函数描述（第一行）
- 参数描述（从 Args/Parameters 部分）

示例：
```python
def my_function(param1: str, param2: int = 10) -> str:
    """
    这是一个有完整文档的函数
    
    Args:
        param1: 第一个参数，很重要
        param2: 第二个参数，有默认值
        
    Returns:
        str: 返回结果
    """
    return f"{param1}, {param2}"
```

转换后的工具定义：
```json
{
  "type": "function",
  "function": {
    "name": "call_namespace__my_function",
    "description": "这是一个有完整文档的函数",
    "parameters": {
      "type": "object",
      "properties": {
        "param1": {
          "type": "string",
          "description": "第一个参数，很重要"
        },
        "param2": {
          "type": "integer",
          "description": "第二个参数，有默认值"
        }
      },
      "required": ["param1"]
    }
  }
}
```

## 依赖更新

已在 `requirements_qt.txt` 中添加：

```txt
mcp>=1.26.0
openai>=1.0.0
python-dotenv>=1.0.0
```

## 向后兼容

如果未安装 `mcp` 包，系统会自动回退到基础类型解析实现：

```python
except ImportError:
    print("[提示] 未安装 mcp 包，使用基础类型解析")
    return self._method_to_openai_tool_basic(method_name, method_func)
```

## 使用方法

### 1. 安装依赖

```bash
pip install -r requirements_qt.txt
```

或单独安装：

```bash
pip install mcp openai python-dotenv
```

### 2. 在插件中使用

只需在插件方法的 `plugin.json` 中配置 `enable_mcp: true`：

```json
{
  "exports": {
    "namespace": "text_helper",
    "methods": [
      {
        "name": "get_text",
        "extra_data": {
          "enable_mcp": true
        }
      }
    ]
  }
}
```

### 3. Agent 会自动处理

当创建 Agent 时，它会自动：
1. 扫描所有启用 MCP 的方法
2. 使用 MCP 的类型解析机制转换为 OpenAI Tool 格式
3. 添加到 LLM 的工具列表中

```python
from app_qt.ipython_llm_bridge import Agent
from app_qt.plugin_manager import get_plugin_manager

plugin_manager = get_plugin_manager()
agent = Agent(plugin_manager=plugin_manager)

# Agent 会自动加载所有启用 MCP 的工具
# agent.ask("请帮我处理这段文本")  # 会自动调用 text_helper.get_text
```

## 测试验证

运行测试脚本验证功能：

```bash
python demos/test_mcp_type_parsing.py
```

预期输出：
```
✓ 所有类型都正确转换！MCP 类型解析机制工作正常
✓ 成功从文档字符串提取参数描述
```

## 技术细节

### 核心方法

1. **`_method_to_openai_tool()`**: 主方法，使用 MCP 进行类型解析
2. **`_method_to_openai_tool_basic()`**: 备用方法，不使用 MCP 时的基础实现
3. **`_infer_param_type()`**: 使用 MCP 类型映射
4. **`_extract_param_description()`**: 从 docstring 提取参数描述
5. **`_extract_function_description()`**: 从 docstring 提取函数描述

### 导入处理

由于这些方法在类内部被调用，每个需要 `inspect` 的方法都单独导入了 `inspect` 模块（使用别名避免冲突）：

```python
import inspect as insp_module
```

## 优势总结

1. **复用成熟框架**：使用 MCP 官方包的类型解析机制
2. **减少代码维护**：不再需要自己维护类型映射表
3. **更好的兼容性**：与 MCP 协议保持一致
4. **更准确的类型推断**：支持复杂的 typing 泛型
5. **自动文档生成**：从 docstring 自动提取描述信息

## 注意事项

1. **MCP 是可选依赖**：如果不安装会回退到基础实现
2. **类型注解必需**：为了让 MCP 正确解析，建议为函数参数添加类型注解
3. **文档字符串推荐**：虽然不是必需的，但推荐使用标准格式的 docstring
