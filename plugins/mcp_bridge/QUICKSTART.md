# MCP Bridge 快速入门

## 1. 安装依赖

```bash
pip install mcp
```

## 2. 配置 MCP 服务器

### 方法一：编辑自动生成的配置文件

首次运行插件时会自动创建配置文件模板，位置在：
```
~/IPythonQTBot/mcp_bridge/config.json
```

编辑该文件，添加你的 MCP 服务器配置：

```json
{
  "mcpServers": {
    "web-search-prime": {
      "type": "streamable-http",
      "url": "https://open.bigmodel.cn/api/mcp/web_search_prime/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

### 方法二：手动创建配置文件

复制 `config.example.json` 到配置目录：

```bash
# Windows PowerShell
mkdir -p $HOME\IPythonQTBot\mcp_bridge
copy config.example.json $HOME\IPythonQTBot\mcp_bridge\config.json

# Linux/Mac
mkdir -p ~/IPythonQTBot/mcp_bridge
cp config.example.json ~/IPythonQTBot/mcp_bridge/config.json
```

然后编辑配置文件。

## 3. 启用插件

在 IPython 中加载插件：

```python
from app_qt.plugin_manager import get_plugin_manager

pm = get_plugin_manager()
pm.load_plugin("mcp_bridge")
```

或者在应用启动时自动加载（如果配置了自动加载）。

## 4. 验证安装

```python
# 查看已配置的服务器
pm.get_method("mcp_bridge.list_servers")()
# 输出：['web-search-prime']

# 等待几秒钟，让插件自动连接服务器
import time
time.sleep(3)

# 获取工具列表
tools = pm.get_method("mcp_bridge.get_mcp_tools")()
print(f"共获取 {len(tools)} 个工具")

# 查看详细工具信息
info = pm.get_method("mcp_bridge.get_tools_info")(detailed=True)
print(info)
```

## 5. 在 LLM 对话中使用

### 示例 1: 网络搜索

```python
# 初始化 LLM Agent（会自动集成 MCP 工具）
from app_qt.ipython_llm_bridge import init_ipython_llm_agent_api

agent = init_ipython_llm_agent_api(plugin_manager=pm)

# 提问，LLM 会自动调用 MCP 搜索工具
agent.ask("请帮我搜索一下最近的 AI 技术突破")
```

### 示例 2: 多轮对话

```python
# 第一轮
agent.ask("搜索 Python 3.13 的新特性")

# 基于搜索结果继续提问
agent.ask("这些特性中哪个最有用？为什么？")
```

### 示例 3: 使用 Magic 命令

```python
# 直接提问
%agent_ask 搜索最新的机器学习论文

# 查看可用工具
agent.show_tools(detailed=True)
```

## 6. 常见问题

### Q: 如何知道 MCP 服务器是否连接成功？

```python
# 查看已连接的服务器
connected = pm.get_method("mcp_bridge.list_connected_servers")()
print(f"已连接的服务器：{connected}")
```

### Q: 工具调用失败怎么办？

1. 检查服务器连接状态
2. 查看详细错误信息
3. 确认 API Key 是否正确
4. 检查网络连接

### Q: 如何添加更多 MCP 服务器？

编辑配置文件 `~/IPythonQTBot/mcp_bridge/config.json`，添加新的服务器配置：

```json
{
  "mcpServers": {
    "server-1": {...},
    "server-2": {...},
    "server-3": {...}
  }
}
```

然后重新加载：

```python
pm.get_method("mcp_bridge.load_mcp_config")("~/IPythonQTBot/mcp_bridge/config.json")
```

## 7. 进阶技巧

### 调试模式

查看详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 手动控制连接

```python
import asyncio
from app_qt.plugin_manager import get_plugin_manager

pm = get_plugin_manager()
mcp_widget = pm.get_plugin("mcp_bridge")["widget"]

# 手动连接特定服务器
asyncio.run(mcp_widget.server_manager.connect_to_server("web-search-prime"))

# 手动断开
asyncio.run(mcp_widget.server_manager.disconnect_from_server("web-search-prime"))
```

### 自定义工具过滤

只暴露部分工具给 LLM：

```python
def filter_tools(tools, keywords):
    """过滤包含关键词的工具"""
    return [t for t in tools if any(k in t['function']['name'] for k in keywords)]

all_tools = pm.get_method("mcp_bridge.get_mcp_tools")()
filtered = filter_tools(all_tools, ["search", "web"])
```

## 8. 下一步

- 阅读完整文档：[README.md](README.md)
- 查看示例配置：[config.example.json](config.example.json)
- 了解如何开发自己的 MCP 服务器

## 9. 获取帮助

遇到问题？

1. 查看 [README.md](README.md) 的故障排查章节
2. 检查日志输出
3. 提交 Issue
