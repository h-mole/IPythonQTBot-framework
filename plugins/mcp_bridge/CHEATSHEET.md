# MCP Bridge 快速参考卡片

## 一分钟快速开始

```bash
# 1. 安装
pip install mcp

# 2. 配置
# 编辑 ~/.myhelper/mcp_bridge/config.json

# 3. 测试
python test_mcp_bridge.py
```

## 配置模板

```json
{
  "mcpServers": {
    "my-server": {
      "type": "streamable-http",
      "url": "https://api.example.com/mcp",
      "headers": {"Authorization": "Bearer YOUR_KEY"}
    }
  }
}
```

## 常用 API

```python
from app_qt.plugin_manager import get_plugin_manager
pm = get_plugin_manager()

# 加载插件
pm.load_plugin("mcp_bridge")

# 列出服务器
pm.get_method("mcp_bridge.list_servers")()

# 获取工具
pm.get_method("mcp_bridge.get_mcp_tools")()

# 查看工具信息
pm.get_method("mcp_bridge.get_tools_info")(detailed=True)
```

## LLM 集成

```python
from app_qt.ipython_llm_bridge import init_ipython_llm_agent_api

agent = init_ipython_llm_agent_api(plugin_manager=pm)
agent.ask("使用 MCP 工具帮我...")
```

## 配置文件位置

```
~/.myhelper/mcp_bridge/config.json
```

## 调试命令

```python
# 检查服务器连接
configured = pm.get_method("mcp_bridge.list_servers")()
connected = pm.get_method("mcp_bridge.list_connected_servers")()

# 查看详细工具
agent.show_tools(detailed=True)
```

## 支持的服务器类型

| 类型 | 配置示例 | 用途 |
|------|----------|------|
| streamable-http | `{"type": "streamable-http", "url": "..."}` | HTTP API |
| stdio | `{"type": "stdio", "command": "python"}` | 本地进程 |

## 工具命名规则

```
MCP 工具名：search.web_search
LLM 工具名：call_mcp__web_search_prime__search__web_search
            └────┘ └─────────────┘ └──────────────────┘
             前缀    服务器名         工具名 (点号→双下划线)
```

## 常见问题速查

### 问题：找不到 mcp 库
```bash
pip install mcp
```

### 问题：服务器未连接
```python
# 等待几秒或手动连接
import time; time.sleep(3)
```

### 问题：工具数量为 0
1. 检查配置是否正确
2. 检查服务器是否可访问
3. 查看错误日志

### 问题：API Key 错误
```json
{
  "headers": {"Authorization": "Bearer 正确的_KEY"}
}
```

## 文档导航

| 需求 | 文档 |
|------|------|
| 快速上手 | [QUICKSTART.md](QUICKSTART.md) |
| 完整功能 | [README.md](README.md) |
| LLM 集成 | [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) |
| 内部结构 | [STRUCTURE.md](STRUCTURE.md) |
| 开发总结 | [DEVELOPMENT_SUMMARY.md](DEVELOPMENT_SUMMARY.md) |

## 快捷键/命令

```python
# IPython 中
agent.ask("问题")          # 提问
agent.clear()              # 清除历史
agent.show_tools()         # 显示工具
%agent_ask 问题            # Magic 命令
```

## 依赖检查

```python
# 检查 MCP 是否可用
try:
    from mcp import ClientSession
    print("MCP 已安装")
except ImportError:
    print("请运行：pip install mcp")
```

## 示例代码片段

### 手动连接服务器
```python
import asyncio
mcp = pm.get_plugin("mcp_bridge")["widget"]
asyncio.run(mcp.server_manager.connect_to_server("server-name"))
```

### 自定义工具过滤
```python
tools = pm.get_method("mcp_bridge.get_mcp_tools")()
search_tools = [t for t in tools if "search" in t["function"]["name"]]
```

### 重新加载配置
```python
pm.get_method("mcp_bridge.load_mcp_config")("~/.myhelper/mcp_bridge/config.json")
```

---

**更多详细信息请查看完整文档** 📚
