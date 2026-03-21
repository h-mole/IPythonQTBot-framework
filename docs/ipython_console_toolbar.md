# IPython 控制台工具条功能说明

## 功能概述

为 IPython 控制台标签页添加了顶部工具条，提供以下功能：

### 1. 清空按钮 (🗑️ 清空)
- **功能**: 一键清空控制台的所有输出内容
- **使用场景**: 当控制台内容过多时，可以快速清理视野
- **实现方法**: `clear_console()`

### 2. 重启按钮 (🔄 重启)
- **功能**: 重启 IPython 内核（重新初始化）
- **使用场景**: 当内核状态异常或需要完全重置环境时
- **实现方法**: `restart_console()`
- **注意**: 会保留已加载的插件和 API，但会清除所有变量

### 3. Agent 状态显示控件

#### 状态指示器
显示当前 Agent 的运行状态：
- **⚪ 空闲**: 初始状态或无任务运行
- **🟢 运行中**: Agent 正在生成回复（此时"停止生成"按钮可见）
- **✅ 生成完毕**: 回答生成完成
- **🔴 错误**: 发生错误

#### 停止生成按钮 (⏹️ 停止生成)
- **功能**: 停止当前正在进行的 LLM 生成任务
- **显示条件**: 仅在"运行中"状态时显示
- **实现方法**: `stop_generation()`

#### Token 计数器 (📊 Tokens: -1)
- **功能**: 显示当前对话上下文的 token 数量
- **默认值**: -1（表示尚未计算）
- **未来扩展**: 可以在 `_on_message_recv` 等方法中调用更新

## 技术实现

### 核心方法

#### `update_status_display(status: str, tokens: int | None = None)`
更新状态显示的通用方法。

**参数**:
- `status`: 状态字符串
  - `"idle"`: 空闲
  - `"generating"`: 生成中
  - `"finished"`: 完成
  - `"error"`: 错误
- `tokens`: token 数量（可选）

**示例**:
```python
# 设置为生成中状态
console_tab.update_status_display(status="generating")

# 更新 token 数量
console_tab.update_status_display(tokens=1500)

# 同时设置状态和 token 数
console_tab.update_status_display(status="finished", tokens=2000)
```

### 自动状态更新

系统会自动在以下情况更新状态：

1. **开始提问时**: `agent.ask()` 会自动设置为 "generating" 状态
2. **文本输出时**: 接收到第一个文本块时标记为生成中
3. **流式输出完成**: 根据下一步动作决定状态
4. **发生错误时**: 自动切换到错误状态

### MCP 工具集成

注册了两个新的 MCP 工具方法：
- `clear_console()`: 清空控制台
- `restart_console()`: 重启控制台

可以通过 LLM Agent 调用这些方法。

## 界面布局

```
┌─────────────────────────────────────────────────────────────┐
│ [🗑️ 清空] [🔄 重启]     [⚪ 空闲] [⏹️ 停止生成] [📊 Tokens: -1] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  IPython Console                               Variables    │
│  ┌─────────────────────────┐  ┌──────────────────────────┐ │
│  │                         │  │                          │ │
│  │   代码执行区域           │  │   变量表格               │ │
│  │                         │  │                          │ │
│  └─────────────────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 样式设计

### 按钮颜色语义
- **清空按钮**: 红色 (#f44336) - 危险操作
- **重启按钮**: 蓝色 (#2196F3) - 重要操作
- **停止按钮**: 橙色 (#FF9800) - 中断操作
- **状态标签**: 
  - 空闲：灰色 (#e0e0e0)
  - 运行中：绿色 (#4CAF50)
  - 完成：蓝色 (#2196F3)
  - 错误：红色 (#f44336)

### 交互效果
所有按钮都支持：
- **悬停**: 颜色加深
- **按下**: 颜色更深
- **圆角**: 4px 圆角设计

## 测试方法

运行测试脚本：
```bash
python test_toolbar.py
```

测试窗口包含一个额外的"测试控件"标签页，可以手动触发各种状态：
- 模拟生成中状态
- 模拟完成状态
- 模拟错误状态
- 模拟空闲状态
- 设置 Token 数量

## 未来扩展

### 1. Token 计数集成
在以下位置添加 token 计数逻辑：
```python
# 在 _on_message_recv 中
def _on_message_recv(self, response: dict):
    # ... 现有代码 ...
    # 计算 token 数
    token_count = self._count_tokens()
    if hasattr(self.ipython_shell, 'parent'):
        console_tab = self.ipython_shell.parent
        console_tab.update_status_display(tokens=token_count)
```

### 2. 进度指示器
可以在状态标签旁边添加进度条或加载动画。

### 3. 快捷键支持
为常用功能添加快捷键：
- Ctrl+L: 清空控制台
- F5: 重启控制台
- Esc: 停止生成

### 4. 历史记录导航
添加上下箭头按钮来浏览历史命令。

## 注意事项

1. **线程安全**: 所有 UI 更新都通过 `exec_main_thread_callback` 在主线程中执行
2. **资源清理**: 关闭窗口时会自动停止内核和清理资源
3. **状态同步**: 避免频繁调用 `update_status_display`，只在必要时更新
4. **类型检查**: 某些 IDE 可能会报告类型错误（如 `Qt.Horizontal`），这是误报，代码可以正常运行

## 相关文件

- `app_qt/ipython_console_tab.py`: 主要实现文件
- `app_qt/ipython_llm_bridge.py`: Agent API，集成了状态通知
- `test_toolbar.py`: 测试脚本
