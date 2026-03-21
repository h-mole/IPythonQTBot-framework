# MCP Bridge 插件目录结构

```
mcp_bridge/
├── README.md                 # 完整功能说明文档
├── QUICKSTART.md             # 快速入门指南
├── INTEGRATION_GUIDE.md      # 与 IPython LLM Bridge 集成指南
├── CHANGELOG.md              # 更新日志
├── config.example.json       # 示例配置文件
├── test_mcp_bridge.py        # 测试脚本
├── .gitignore               # Git 忽略文件
│
├── main.py                  # 插件主程序
│   ├── MCPServerManager     # MCP 服务器管理器
│   │   ├── load_config()           # 加载配置
│   │   ├── connect_to_server()     # 连接服务器
│   │   ├── disconnect_from_server()# 断开服务器
│   │   ├── get_all_tools()         # 获取所有工具
│   │   └── call_tool()             # 调用工具
│   │
│   └── MCPBridgeWidget      # 插件组件
│       ├── load_mcp_config()       # 加载配置
│       ├── connect_all_servers()   # 连接所有服务器
│       ├── get_mcp_tools_for_llm() # 获取 LLM 格式工具
│       ├── list_servers()          # 列出服务器
│       └── get_tools_info()        # 获取工具信息
│
└── plugin.json              # 插件描述文件
    ├── name: mcp_bridge
    ├── description: MCP 工具桥接插件
    ├── version: 1.0.0
    ├── dependencies: package:mcp
    └── exports.methods:
        ├── load_mcp_config
        ├── get_mcp_tools
        ├── list_servers
        └── get_tools_info
```

## 核心组件说明

### 1. MCPServerManager (main.py)

MCP 服务器的核心管理类，负责：
- 解析 JSON 配置文件
- 建立与 MCP 服务器的连接（HTTP 或 stdio）
- 获取并缓存工具列表
- 执行工具调用

关键方法：
```python
async def connect_to_server(server_name: str) -> bool
async def disconnect_from_server(server_name: str) -> bool
def get_all_tools() -> List[Dict]
async def call_tool(tool_name: str, arguments: Dict) -> Any
```

### 2. MCPBridgeWidget (main.py)

插件的功能组件，提供对外的 API 接口：
- 自动加载配置文件
- 后台异步连接所有服务器
- 将 MCP 工具转换为 LLM 可用的格式
- 提供工具信息查询

关键方法：
```python
def load_mcp_config(config_path: str) -> bool
async def connect_all_servers() -> bool
def get_mcp_tools_for_llm() -> List[Dict]
def list_servers() -> List[str]
def get_tools_info(detailed: bool) -> str
```

### 3. plugin.json

插件的元数据定义：
- 插件名称、版本、描述
- 依赖关系（mcp 包）
- 导出的方法列表及其签名
- 启用 MCP 标记（enable_mcp）

### 4. 配置文件 (config.json)

MCP 服务器配置：
```json
{
  "mcpServers": {
    "server-name": {
      "type": "streamable-http",
      "url": "https://...",
      "headers": {...}
    }
  }
}
```

## 数据流

### 工具映射流程

```
MCP Server
  ↓ (list_tools)
MCP Tool {name, description, inputSchema}
  ↓ (添加服务器前缀)
Prefixed Tool {server__tool.name}
  ↓ (转换为 OpenAI 格式)
LLM Tool {type: "function", function: {...}}
  ↓ (注册到 LLM)
可用工具
```

### 工具调用流程

```
用户提问
  ↓
LLM 分析 → 决定调用工具
  ↓
返回 tool_call {name: "call_mcp__server__tool", arguments: {...}}
  ↓
IPython LLM Bridge 解析
  ↓
识别为 MCP 工具
  ↓
MCPServerManager.call_tool()
  ↓
MCP Server 执行
  ↓
返回结果
  ↓
LLM 生成最终答案
```

## 与其他组件的关系

```
┌─────────────────────────┐
│   IPython LLM Bridge    │
│   (ipython_llm_bridge)  │
└───────────┬─────────────┘
            │ 使用
            ↓
┌─────────────────────────┐
│    Plugin Manager       │
│   (plugin_manager)      │
└───────────┬─────────────┘
            │ 加载
            ↓
┌─────────────────────────┐
│    MCP Bridge Plugin    │
│      (main.py)          │
└───────────┬─────────────┘
            │ 连接
            ↓
┌─────────────────────────┐
│    MCP Servers          │
│  (HTTP / stdio)         │
└─────────────────────────┘
```

## 文件用途总结

| 文件 | 行数 | 用途 |
|------|------|------|
| main.py | ~470 | 核心实现 |
| plugin.json | ~85 | 插件元数据 |
| README.md | ~280 | 完整文档 |
| QUICKSTART.md | ~200 | 快速入门 |
| INTEGRATION_GUIDE.md | ~370 | 集成指南 |
| config.example.json | ~20 | 配置示例 |
| test_mcp_bridge.py | ~180 | 测试脚本 |
| CHANGELOG.md | ~55 | 更新日志 |
| .gitignore | ~44 | Git 忽略规则 |

**总计**: 约 1900 行代码和文档

## 依赖关系

```
requirements:
  - mcp >= 1.0.0     # MCP SDK
  - PySide6          # Qt 集成（通过项目依赖）
  - asyncio          # Python 内置
```

## 环境要求

- Python 3.8+
- Windows / Linux / Mac
- 网络连接（用于 HTTP MCP 服务器）
- 相应的命令行工具（用于 stdio MCP 服务器）
