# MCP Bridge Plugin

MCP（Model Context Protocol）工具桥接插件，用于将 MCP 服务器的工具映射为 LLM（Large Language Model）可调用的 tools。

## 功能特性

- ✅ 从 JSON 配置文件导入 MCP 服务器配置
- ✅ 支持 HTTP 流式（streamable-http）和标准输入输出（stdio）两种连接方式
- ✅ 自动获取并缓存 MCP 工具列表
- ✅ 将 MCP 工具转换为 OpenAI Tool 格式
- ✅ 与 IPython LLM Bridge 无缝集成
- ✅ 支持多 MCP 服务器同时连接

## 安装

### 1. 安装依赖

```bash
pip install mcp
```

### 2. 启用插件

在插件管理器中启用 `mcp_bridge` 插件。

## 配置

### 配置文件位置

配置文件默认位于：`~/.myhelper/mcp_bridge/config.json`

首次加载插件时会自动创建示例配置文件。

### 配置格式

```json
{
  "mcpServers": {
    "web-search-prime": {
      "type": "streamable-http",
      "url": "https://open.bigmodel.cn/api/mcp/web_search_prime/mcp",
      "headers": {
        "Authorization": "Bearer your_api_key"
      }
    },
    "local-tool-server": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mcp_server"],
      "env": {
        "API_KEY": "your_api_key"
      }
    }
  }
}
```

### 配置说明

#### HTTP 流式服务器（streamable-http）

- `type`: `"streamable-http"`
- `url`: MCP 服务器的 HTTP 端点 URL
- `headers`: （可选）HTTP 请求头，常用于身份认证

#### 标准输入输出服务器（stdio）

- `type`: `"stdio"`
- `command`: 启动命令（如 `python`, `node` 等）
- `args`: （可选）命令行参数
- `env`: （可选）环境变量

## 使用方法

### 1. 在 IPython 中使用

```python
# 查看可用的 MCP 工具
agent.show_tools(detailed=True)

# 或者使用 magic 命令
%agent_show_tools

# LLM 会自动调用 MCP 工具
agent.ask("请帮我搜索一下今天的科技新闻")
```

### 2. API 调用

```python
from app_qt.plugin_manager import get_plugin_manager

pm = get_plugin_manager()

# 手动加载配置
pm.get_method("mcp_bridge.load_mcp_config")("/path/to/config.json")

# 获取工具列表
tools = pm.get_method("mcp_bridge.get_mcp_tools")()
print(tools)

# 查看服务器列表
servers = pm.get_method("mcp_bridge.list_servers")()
print(servers)

# 获取工具信息文本
info = pm.get_method("mcp_bridge.get_tools_info")(detailed=True)
print(info)
```

## 工作原理

### 工具名称映射

MCP Bridge 会将 MCP 工具名称转换为 LLM 可识别的格式：

- **原始工具名**: `search.web_search`
- **转换后**: `call_mcp__web_search_prime__search__web_search`

格式：`call_mcp__{server_name}__{tool_name}`（工具名中的点号会被转换为双下划线）

### 工具调用流程

1. LLM 决定调用工具 → 返回工具名称和参数
2. IPython LLM Bridge 解析工具名称 → 识别为 MCP 工具
3. 通过 `MCPServerManager.call_tool()` 调用对应的 MCP 工具
4. 将结果返回给 LLM → LLM 继续生成响应

## 与 IPython LLM Bridge 集成

MCP Bridge 插件会自动将工具注册到 LLM Bridge：

```python
# 在 IPython LLM Bridge 初始化时
# init_ipython_llm_agent_api() 会自动：
# 1. 连接到所有配置的 MCP 服务器
# 2. 获取工具列表并转换为 OpenAI Tool 格式
# 3. 添加到 LLM 的 tools 参数中
```

## 示例场景

### 场景 1: 网络搜索

配置 web-search-prime MCP 服务器后，LLM 可以自动调用搜索工具：

```python
agent.ask("帮我查一下最近 AI 领域的重大突破")
# LLM 会自动调用 search.web_search 工具获取最新信息
```

### 场景 2: 本地文件操作

配置本地文件操作 MCP 服务器：

```json
{
  "file-manager": {
    "type": "stdio",
    "command": "mcp-file-server",
    "args": ["--root", "/home/user/documents"]
  }
}
```

LLM 可以操作文件：

```python
agent.ask("帮我列出 documents 目录下的所有 PDF 文件")
```

## 故障排查

### 问题 1: MCP 库未安装

**错误信息**: `[MCP Bridge] 警告：未安装 mcp 库`

**解决方法**:
```bash
pip install mcp
```

### 问题 2: 服务器连接失败

**检查项**:
- 配置文件路径是否正确
- URL 或命令是否配置正确
- 网络连接是否正常（对于 HTTP 服务器）
- 命令行工具是否可用（对于 stdio 服务器）

### 问题 3: 工具调用失败

**可能原因**:
- MCP 服务器未正确连接
- 工具名称拼写错误
- 参数格式不符合要求

**解决方法**:
```python
# 查看已连接的服务器
pm.get_method("mcp_bridge.list_connected_servers")()

# 查看详细工具信息
pm.get_method("mcp_bridge.get_tools_info")(detailed=True)
```

## 高级用法

### 动态添加服务器

```python
# 运行时动态修改配置
config = {
    "mcpServers": {
        "new-server": {
            "type": "streamable-http",
            "url": "https://example.com/mcp"
        }
    }
}

import json
with open("~/.myhelper/mcp_bridge/config.json", "w") as f:
    json.dump(config, f)

# 重新加载配置
pm.get_method("mcp_bridge.load_mcp_config")("~/.myhelper/mcp_bridge/config.json")
```

### 手动控制服务器连接

```python
import asyncio
from app_qt.plugin_manager import get_plugin_manager

pm = get_plugin_manager()
mcp_widget = pm.get_plugin("mcp_bridge")["widget"]

# 连接特定服务器
asyncio.run(mcp_widget.server_manager.connect_to_server("web-search-prime"))

# 断开连接
asyncio.run(mcp_widget.server_manager.disconnect_from_server("web-search-prime"))
```

## API 参考

### MCPServerManager

- `load_config(config_path: str) -> bool`: 加载配置文件
- `connect_to_server(server_name: str) -> bool`: 连接到指定服务器
- `disconnect_from_server(server_name: str) -> bool`: 断开指定服务器
- `get_all_tools() -> List[Dict]`: 获取所有工具
- `call_tool(tool_name: str, arguments: Dict) -> Any`: 调用工具

### MCPBridgeWidget

- `load_mcp_config(config_path: str) -> bool`: 加载配置
- `connect_all_servers() -> bool`: 连接所有服务器
- `get_mcp_tools_for_llm() -> List[Dict]`: 获取 LLM 格式工具
- `list_servers() -> List[str]`: 列出已配置服务器
- `get_tools_info(detailed: bool) -> str`: 获取工具信息

## 注意事项

1. **安全性**: MCP 服务器可能具有访问本地文件或网络的权限，请仅连接可信的服务器
2. **性能**: 工具调用会增加 LLM 响应时间，建议合理控制工具数量
3. **错误处理**: 工具调用失败时，错误信息会反馈给 LLM，LLM 可能会尝试其他方式

## 开发计划

- [ ] 支持服务器自动重连
- [ ] 添加工具调用日志记录
- [ ] 支持工具调用的权限控制
- [ ] 提供服务器状态监控界面

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
