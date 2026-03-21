# Agent 历史对话功能 - 快速参考

## 📁 存储位置

```
~/myhelper/app_data/llm_conversation_history/
├── conversation_20250322_143022.json
├── conversation_20250322_120000.json
└── conversation_20250321_180000.json
```

## ⚡ 核心 API

### 自动保存
```python
# 每次调用 agent.ask() 时自动保存
agent.ask("你好")  # 自动保存到带时间戳的文件
```

### 列出最近对话
```python
agent.list_recent_conversations()      # 默认显示最近 10 个
agent.list_recent_conversations(limit=5)  # 显示最近 5 个
```

### 加载对话
```python
agent.load_history()  # 自动加载最近的对话
agent.load_history('conversation_20250322_143022.json')  # 加载指定文件
```

### 手动保存
```python
agent.save_history()  # 使用当前文件名保存
agent.save_history('important.json')  # 保存到自定义文件
```

## 🎯 典型使用场景

### 场景 1: 日常对话（全自动）
```python
# 开始对话 - 自动创建并保存
agent.ask("帮我写个 Python 函数")
# → 自动保存为 conversation_20250322_143022.json

# 继续对话 - 自动更新同一文件
agent.ask("能优化一下吗？")
# → 继续保存到同一文件

# 清除并开始新对话
agent.clear()

# 下次提问会创建新文件
agent.ask("新项目需要什么架构？")
# → 创建新的 conversation_20250322_150000.json
```

### 场景 2: 多项目管理
```python
# 项目 A
agent.ask("项目 A 的数据库设计")
# → conversation_A_time1.json

agent.clear()

# 项目 B
agent.ask("项目 B 的 API 设计")
# → conversation_B_time2.json

# 切换回项目 A
agent.load_history('conversation_A_time1.json')
```

### 场景 3: 查找和恢复
```python
# 查看所有历史对话
agent.list_recent_conversations()
# [Agent] 找到 5 个历史对话文件:
#   1. conversation_20250322_143022.json (最新)
#   2. conversation_20250322_120000.json
#   3. conversation_20250321_180000.json
#   ...

# 加载最近的
agent.load_history()  # 自动选择最新的

# 加载指定的
agent.load_history('conversation_20250321_180000.json')
```

## 📋 JSON 文件结构

```json
{
  "messages": [...],                      // 完整对话历史
  "mcp_tools_enabled": ["tool1", "tool2"], // 启用的工具
  "mcp_tools_disabled": ["tool3"],         // 禁用的工具
  "config": {                             // LLM 配置
    "provider": "aliyun",
    "model": "glm-5"
  },
  "conversation_start_time": "20250322_143022"  // 时间戳
}
```

## 🔧 Magic 命令

```python
%agent_ask <问题>     # 提问并自动保存
%agent_clear         # 清除当前对话
%agent_messages      # 查看消息历史
```

## 💡 最佳实践

### ✅ 推荐做法
1. **依赖自动保存**: 不需要手动调用 `save_history()`
2. **定期清理**: 使用 `list_recent_conversations()` 查看后删除旧文件
3. **项目分离**: 不同项目使用不同的对话文件
4. **及时清除**: 开始新话题前调用 `agent.clear()`

### ❌ 避免的做法
1. ~~不要手动编辑 JSON 文件~~ (可能导致格式错误)
2. ~~不要在对话中删除文件~~ (可能导致保存失败)
3. ~~不要共享包含 API Key 的文件~~ (安全风险)

## 🛠️ 故障排除

### 问题：找不到历史文件
```python
# 检查目录是否存在
from pathlib import Path
from app_qt.configs import MAIN_APP_DATA_DIR

history_dir = MAIN_APP_DATA_DIR / "llm_conversation_history"
print(f"历史目录：{history_dir}")
print(f"目录存在：{history_dir.exists()}")
```

### 问题：加载失败
```python
# 尝试加载其他文件
agent.list_recent_conversations()
agent.load_history('conversation_*.json')  # 换个文件试试
```

## 📊 文件管理技巧

### 批量查看
```python
import os
from pathlib import Path
from app_qt.configs import MAIN_APP_DATA_DIR

history_dir = MAIN_APP_DATA_DIR / "llm_conversation_history"
files = list(history_dir.glob("conversation_*.json"))
print(f"共有 {len(files)} 个历史对话文件")
```

### 清理旧文件
```python
import time

# 删除 30 天前的文件
threshold = time.time() - (30 * 24 * 60 * 60)
for file in history_dir.glob("conversation_*.json"):
    if file.stat().st_mtime < threshold:
        file.unlink()
        print(f"已删除：{file.name}")
```

## 🚀 快速上手

1. **开始使用**
   ```python
   agent.ask("你好")  # 就这么简单，自动保存
   ```

2. **查看历史**
   ```python
   agent.list_recent_conversations()
   ```

3. **恢复对话**
   ```python
   agent.load_history()  # 自动加载最近的
   ```

就是这么简单！🎉
