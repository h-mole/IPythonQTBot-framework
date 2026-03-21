# Agent 历史对话功能实现总结

## 📝 需求变更

### 原始需求
- 保存历史对话消息记录为 JSON 格式
- 包含 `messages` 和 `mcp_tools_enabled` 状态

### 新需求（最终实现）
1. ✅ 保存到 `configs.MAIN_APP_DATA_DIR/llm_conversation_history` 文件夹
2. ✅ 每次 `agent.messages` 增加新消息时自动保存
3. ✅ 文件名包含对话开始时间信息（格式：`conversation_YYYYMMDD_HHMMSS.json`）
4. ✅ 提供 API 列出最近的对话
5. ✅ 提供 API 加载最近的 messages

## 🔧 核心实现

### 1. 目录结构

```python
# 在 Agent.__init__ 中
self.history_dir = MAIN_APP_DATA_DIR / "llm_conversation_history"
if not self.history_dir.exists():
    self.history_dir.mkdir(parents=True, exist_ok=True)
```

### 2. 时间戳记录

```python
# 在 agent.ask() 中，首次提问时记录时间
if self.conversation_start_time is None:
    from datetime import datetime
    self.conversation_start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
```

### 3. 自动保存机制

```python
# 用户消息添加后自动保存
self.messages.append({"role": "user", "content": prompt})
self._auto_save()

# AI 响应添加后自动保存
self.messages.append(response)
self._auto_save()
```

### 4. 智能文件命名

```python
def save_history(self, file_path: str | None = None):
    if file_path is None:
        # 自动生成文件名：conversation_YYYYMMDD_HHMMSS.json
        timestamp = self.conversation_start_time or "unknown"
        file_name = f"conversation_{timestamp}.json"
        file_path = str(self.history_dir / file_name)
```

### 5. 列出最近对话

```python
def list_recent_conversations(self, limit: int = 10) -> list[str]:
    # 使用 glob 查找所有 conversation_*.json
    # 按修改时间排序（最新的在前）
    # 返回前 N 个文件的路径
```

### 6. 智能加载

```python
def load_history(self, file_path: str | None = None):
    if file_path is None:
        # 自动加载最近的文件
        recent_files = self.list_recent_conversations(limit=1)
        if not recent_files:
            return False
        file_path = recent_files[0]
```

## 📊 数据结构

### JSON 文件格式
```json
{
    "messages": [...],                      // 完整对话历史
    "mcp_tools_enabled": ["tool1", "tool2"], // 启用的工具名称列表
    "mcp_tools_disabled": ["tool3"],         // 禁用的工具名称列表
    "config": {                             // LLM 配置
        "provider": "aliyun",
        "api_key": "...",
        "base_url": "...",
        "model": "..."
    },
    "conversation_start_time": "20250322_143022"  // 对话开始时间戳
}
```

## 🎯 关键 API

### 自动保存（内置）
- `agent.ask("问题")` - 提问并自动保存
- `_auto_save()` - 内部调用，保存到当前文件

### 列出对话
- `list_recent_conversations(limit=10)` - 列出最近 N 个对话文件

### 加载对话
- `load_history()` - 自动加载最近的对话
- `load_history('conversation_*.json')` - 加载指定文件

### 手动保存
- `save_history()` - 使用自动生成文件名保存
- `save_history('custom.json')` - 保存到自定义文件

## 🔄 工作流程

### 典型对话流程

```
1. 用户调用 agent.ask("你好")
   ↓
2. 检测到是对话开始，记录时间戳 (20250322_143022)
   ↓
3. 添加用户消息到 messages
   ↓
4. 自动保存到 conversation_20250322_143022.json
   ↓
5. LLM 处理并返回响应
   ↓
6. 添加 AI 响应到 messages
   ↓
7. 再次自动保存到同一文件
   ↓
8. 用户继续提问... (重复步骤 3-7)
```

### 清除和新建对话

```
1. 用户调用 agent.clear()
   ↓
2. 清空 messages 列表
   ↓
3. 重置 conversation_start_time 为 None
   ↓
4. 重置 current_history_file 为 None
   ↓
5. 下次提问时会创建新的对话文件
```

## 📁 文件系统

### 目录结构
```
~/myhelper/
└── app_data/
    └── llm_conversation_history/
        ├── conversation_20250322_143022.json
        ├── conversation_20250322_120000.json
        ├── conversation_20250321_180000.json
        └── ...
```

### 文件命名规则
- **前缀**: `conversation_`
- **时间戳**: `YYYYMMDD_HHMMSS` (精确到秒)
- **扩展名**: `.json`
- **示例**: `conversation_20250322_143022.json`

## 🔍 文件管理

### 查找文件
```python
# 使用 glob 模式匹配
pattern = str(self.history_dir / "conversation_*.json")
files = glob.glob(pattern)
```

### 排序文件
```python
# 按修改时间倒序排列
files_with_mtime = [(f, os.path.getmtime(f)) for f in files]
files_with_mtime.sort(key=lambda x: x[1], reverse=True)
```

### 显示信息
```python
for i, file_path in enumerate(result, 1):
    mtime = os.path.getmtime(file_path)
    time_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    print(f"  {i}. {os.path.basename(file_path)} ({time_str})")
```

## ⚠️ 注意事项

### 安全性
1. **API Key 保护**: JSON 文件包含敏感信息，不应提交到版本控制
2. **文件权限**: 建议设置适当的文件访问权限
3. **隐私数据**: 敏感对话应定期清理

### 性能优化
1. **自动保存频率**: 每次消息更新都保存，小文件无性能问题
2. **文件大小**: 长期对话可能产生大文件，建议定期清理
3. **清理策略**: 可定期删除旧文件（如 30 天前的）

### 兼容性
1. **向后兼容**: 支持加载不带时间戳的旧文件
2. **配置恢复**: 可选恢复 LLM 配置，避免冲突
3. **工具变化**: 工具不存在时会跳过，不影响加载

## 📈 改进点

### 已实现
- ✅ 自动保存到专用目录
- ✅ 带时间戳的文件命名
- ✅ 列出最近对话
- ✅ 智能加载最近文件
- ✅ 完整的状态持久化

### 未来可能的改进
- 💡 对话压缩（减少存储空间）
- 💡 对话标签（方便分类管理）
- 💡 增量保存（提高性能）
- 💡 云同步（跨设备访问）
- 💡 搜索功能（快速找到特定对话）

## 📚 相关文档

1. **详细文档**: `docs/agent_history_feature.md`
2. **快速参考**: `docs/agent_history_quickref.md`
3. **测试脚本**: `test_agent_history.py`
4. **源代码**: `app_qt/ipython_llm_bridge.py`

## 🎉 总结

本次实现完全满足新需求：
1. ✅ 保存到指定目录 (`MAIN_APP_DATA_DIR/llm_conversation_history`)
2. ✅ 每次消息更新时自动保存
3. ✅ 文件名包含时间戳信息
4. ✅ 提供列出最近对话的 API
5. ✅ 提供智能加载最近对话的 API

用户体验得到显著提升：
- **零配置**: 无需手动设置，开箱即用
- **自动化**: 所有保存操作都是自动的
- **易管理**: 轻松查看和切换历史对话
- **可靠性**: 每次对话都完整保存，不会丢失

代码质量：
- **类型安全**: 完整的类型注解
- **错误处理**: 完善的异常捕获
- **可维护性**: 清晰的代码结构和注释
- **可扩展性**: 易于添加新功能
