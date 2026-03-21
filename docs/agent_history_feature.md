# Agent 历史对话保存功能

## 功能概述

`ipython_llm_bridge.py` 中的 Agent 类支持自动保存和加载历史对话，包括:
- 完整的对话消息历史 (`messages`)
- MCP 工具启用/禁用状态 (`mcp_tools_enabled`, `mcp_tools_disabled`)
- LLM 配置信息 (`config`)
- 对话开始时间戳 (`conversation_start_time`)

## 存储位置和命名

### 存储目录
所有历史对话文件保存在：
```
~/myhelper/app_data/llm_conversation_history/
```

### 文件命名格式
```
conversation_YYYYMMDD_HHMMSS.json
```
例如：`conversation_20250322_143022.json`

### 自动保存机制
每次调用 `agent.ask()` 添加新消息时，都会自动保存到当前对话文件中。

## JSON 文件格式

保存的 JSON 文件包含以下结构:

```json
{
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant..."
        },
        {
            "role": "user",
            "content": "你好"
        },
        {
            "role": "assistant",
            "content": "你好！有什么我可以帮助你的吗？",
            "reasoning_content": "用户打招呼，应该友好回应"
        }
    ],
    "mcp_tools_enabled": ["text_helper.get_text", "email_utils.send_email"],
    "mcp_tools_disabled": ["mcp_bridge.search_web"],
    "config": {
        "provider": "aliyun",
        "api_key": "sk-xxx",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "glm-5"
    },
    "conversation_start_time": "20250322_143022"
}
```

## API 使用

### 1. 自动保存（默认行为）

每次调用 `agent.ask()` 时会自动保存对话到：
```
~/myhelper/app_data/llm_conversation_history/conversation_YYYYMMDD_HHMMSS.json
```

第一次提问时会自动记录对话开始时间并生成文件名。

### 2. 列出最近的对话

```python
# 列出最近 10 个对话
agent.list_recent_conversations()

# 列出最近 N 个对话
agent.list_recent_conversations(limit=5)
```

输出示例：
```
[Agent] 找到 3 个历史对话文件:
  1. conversation_20250322_143022.json (2025-03-22 14:30:22)
  2. conversation_20250322_120000.json (2025-03-22 12:00:00)
  3. conversation_20250321_180000.json (2025-03-21 18:00:00)
```

### 3. 加载历史对话

```python
# 自动加载最近的对话
agent.load_history()

# 从指定文件加载
agent.load_history('conversation_20250322_143022.json')
```

### 4. 手动保存

```python
# 使用自动生成文件名（基于对话开始时间）
agent.save_history()

# 保存到指定文件（自定义文件名）
agent.save_history('important_discussion.json')
```

### 5. Magic 命令

在 IPython 控制台中，还可以使用 magic 命令:

```python
%agent_ask <问题>          # 提问（自动保存）
%agent_clear               # 清除历史
%agent_messages            # 显示历史消息
```

## 完整使用示例

### 示例 1: 自动保存和恢复对话

```python
# 第一次提问，开始新对话
agent.ask("你好，请帮我写一个排序算法")
# 输出：[Agent] 新对话已开始，时间：20250322_143022
# 自动保存到：conversation_20250322_143022.json

# 继续提问（自动保存）
agent.ask("能再优化一下性能吗？")

# ... 多轮对话后 ...

# 查看最近的对话
agent.list_recent_conversations()

# 清除当前对话
agent.clear()

# 加载最近的对话（自动找到 conversation_20250322_143022.json）
agent.load_history()

# 继续讨论
agent.ask("刚才说的排序算法，能再优化一下吗？")
```

### 示例 2: 管理多个对话场景

```python
# 项目 A 的讨论（自动保存）
agent.ask("帮我设计一个数据库 schema")
# 自动保存为：conversation_20250322_090000.json

# 清除并开始新项目
agent.clear()

# 项目 B 的讨论（自动保存）
agent.ask("项目 B 需要什么样的 API 架构？")
# 自动保存为：conversation_20250322_100000.json

# 查看所有对话
agent.list_recent_conversations()
# 输出:
#   1. conversation_20250322_100000.json (项目 B)
#   2. conversation_20250322_090000.json (项目 A)

# 切换到项目 A 的对话
agent.load_history('conversation_20250322_090000.json')

# 切换到项目 B 的对话
agent.load_history('conversation_20250322_100000.json')
```

### 示例 3: 工具状态管理

```python
# 启用特定工具
agent.update_mcp_tools_filter(
    enabled_tools=["text_helper.get_text", "text_helper.render_markdown"],
    disabled_tools=["mcp_bridge.search_web"]
)

# 保存当前状态 (包括工具配置)
agent.save_history()

# 下次加载时会恢复相同的工具启用/禁用状态
agent.load_history()
```

## 实现细节

### 自动保存流程

1. 首次调用 `agent.ask()` 时：
   - 记录对话开始时间 `conversation_start_time`
   - 生成文件名 `conversation_YYYYMMDD_HHMMSS.json`
   
2. 每次添加消息时：
   - 用户消息添加到 `messages` 后立即保存
   - AI 响应添加到 `messages` 后立即保存
   
3. 保存内容：
   - 完整的 `messages` 列表
   - `mcp_tools_enabled` 和 `mcp_tools_disabled` 集合
   - LLM 配置信息
   - 对话开始时间戳

### 加载流程

1. 如果没有指定文件，自动查找最近的文件
2. 从 JSON 文件读取数据
3. 恢复 `messages` 列表
4. 调用 `update_mcp_tools_filter()` 恢复工具状态
5. 恢复对话开始时间
6. 可选：恢复 LLM 配置并重新创建客户端

### 文件管理

- **目录**: `MAIN_APP_DATA_DIR/llm_conversation_history/`
- **文件名格式**: `conversation_*.json`
- **排序方式**: 按文件修改时间倒序（最新的在前）
- **清理建议**: 定期删除旧文件，或使用 `list_recent_conversations(limit=N)` 只查看最近的 N 个

## 注意事项

1. **API Key 安全**: 保存的文件包含 API Key，请妥善保管，不要提交到版本控制系统
2. **自动保存**: 每次提问或收到回复时都会自动保存，无需手动调用
3. **文件覆盖**: 同一对话的所有消息都保存在同一个文件中，不会覆盖其他对话
4. **工具兼容性**: 加载时如果某些工具已不存在，可能会被忽略
5. **配置冲突**: 加载的配置可能与当前环境不同，注意检查
6. **隐私保护**: 敏感对话建议定期清理或使用后删除

## 相关文件

- 核心实现：`app_qt/ipython_llm_bridge.py`
- 测试脚本：`test_agent_history.py`
- 配置目录：`app_qt/configs.py` 中定义的 `MAIN_APP_DATA_DIR`
- 存储位置：`~/myhelper/app_data/llm_conversation_history/`

## 类型注解说明

代码中使用了严格的类型注解:
- `file_path: str | None` - 文件路径可以是字符串或 None
- `mcp_tools_enabled: set[str]` - 工具名称的集合
- `Optional["Agent"]` - 可选的 Agent 实例引用

这些注解有助于 IDE 提供代码提示和类型检查。
