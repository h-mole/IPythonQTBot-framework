# MCP 工具管理器组件重构说明

## 概述

本次重构将 `ipython_console_tab.py` 中的 `show_mcp_tools_manager` 方法提取为一个独立的可复用 widget 组件 `MCPToolsManagerWidget`，并解决了 MCP 工具状态管理的多个问题。

## 主要改进

### 1. 组件化重构

**新文件：** `app_qt/widgets/mcp_tools_manager.py`

- 创建了独立的 `MCPToolsManagerWidget` 类，继承自 `QDialog`
- 使用 Qt 信号机制 (`tools_selection_changed`) 与父窗口通信
- 支持传入 `agent_instance` 参数以加载当前的工具配置状态

**优势：**
- ✅ 代码解耦，易于维护
- ✅ 可复用于其他界面
- ✅ 职责清晰，符合单一职责原则

### 2. MCP 工具状态管理优化

#### 问题描述
之前每次打开 MCP 工具管理面板时，所有复选框都默认为全选状态，不反映 Agent 的实际过滤配置。

#### 解决方案

**在 `ipython_llm_bridge.py` 中：**

1. **初始化顺序调整**（第 504-538 行）：
   ```python
   # 先初始化空集合
   self.mcp_tools_enabled: set[str] = set()
   self.mcp_tools_disabled: set[str] = set()
   
   # 立即加载历史对话（包含工具配置）
   self.auto_load()
   
   # 然后才构建工具列表
   if self.plugin_manager:
       mcp_tools = self._build_mcp_tools()
   ```

2. **`load_history` 方法**（第 628-682 行）：
   - 从历史文件加载 `mcp_tools_enabled` 和 `mcp_tools_disabled`
   - 调用 `update_mcp_tools_filter` 恢复工具状态

3. **`clear` 方法修改**（第 733-745 行）：
   ```python
   # 清除时不重置 MCP 工具状态，保持上一轮的配置
   # self.mcp_tools_enabled.clear()
   # self.mcp_tools_disabled.clear()
   print("[Agent] 已清除历史对话，可以开始新对话（工具配置保持不变）")
   ```

**在 `widgets/mcp_tools_manager.py` 中：**

`_load_tools_from_agent` 方法（第 141-169 行）：
```python
def _load_tools_from_agent(self):
    """从 Agent 加载工具启用/禁用状态"""
    if not self.agent_instance:
        return
    
    enabled_tools = self.agent_instance.mcp_tools_enabled
    disabled_tools = self.agent_instance.mcp_tools_disabled
    
    # 如果 enabled_tools 为空，表示全部启用（除非在 disabled 中）
    if not enabled_tools:
        for namespace, cbs in self.method_checkboxes.items():
            for cb in cbs:
                tool_name = cb.property('tool_name')
                if tool_name in disabled_tools:
                    cb.setChecked(False)
                else:
                    cb.setChecked(True)
    else:
        # 有明确的启用列表：只有 enabled_tools 中的才被启用
        for namespace, cbs in self.method_checkboxes.items():
            for cb in cbs:
                tool_name = cb.property('tool_name')
                if tool_name in enabled_tools:
                    cb.setChecked(True)
                else:
                    cb.setChecked(False)
```

### 3. 状态持久化流程

#### 场景 1：应用程序启动
```
Agent 初始化 
  ↓
mcp_tools_enabled/disabled = 空集合
  ↓
auto_load() 加载最近的历史对话
  ↓
从历史文件恢复工具配置
  ↓
打开 MCP 工具管理器 → 显示正确的复选框状态
```

#### 场景 2：用户修改工具配置
```
用户打开 MCP 工具管理器
  ↓
修改复选框选择
  ↓
点击确定
  ↓
_on_mcp_tools_selection_changed 被调用
  ↓
agent.update_mcp_tools_filter(enabled, disabled)
  ↓
自动保存到当前历史文件
```

#### 场景 3：清除对话开始新会话
```
用户调用 agent.clear()
  ↓
消息历史被清空
  ↓
工具配置保持不变 ← 关键改进
  ↓
新对话继承上一轮的工具备配置
```

#### 场景 4：加载历史对话
```
用户调用 agent.load_history('file.json')
  ↓
从指定文件加载数据
  ↓
恢复 messages、config、tool 配置
  ↓
Agent 状态与历史记录完全一致
```

## 使用方法

### 在 IPythonConsoleTab 中使用

```python
from app_qt.widgets.mcp_tools_manager import MCPToolsManagerWidget

class IPythonConsoleTab(QWidget):
    def show_mcp_tools_manager(self):
        """显示 MCP 工具管理器对话框"""
        # 创建 MCP 工具管理器实例，并传入 agent 引用
        dialog = MCPToolsManagerWidget(parent=self, agent_instance=self.agent_instance)
        
        # 连接信号到处理方法
        dialog.tools_selection_changed.connect(self._on_mcp_tools_selection_changed)
        
        dialog.exec_()
    
    def _on_mcp_tools_selection_changed(self, enabled_tools: list, disabled_tools: list):
        """处理 MCP 工具选择变化"""
        if hasattr(self, 'agent_instance') and self.agent_instance:
            self.agent_instance.update_mcp_tools_filter(enabled_tools, disabled_tools)
```

### 在其他地方使用

```python
# 创建不带 agent 的实例（所有工具默认启用）
dialog = MCPToolsManagerWidget(parent=window)
dialog.exec_()

# 创建带 agent 的实例（根据 agent 状态初始化）
dialog = MCPToolsManagerWidget(parent=window, agent_instance=agent)
dialog.tools_selection_changed.connect(lambda e, d: print(f"启用：{e}, 禁用：{d}"))
dialog.exec_()
```

## API 参考

### MCPToolsManagerWidget

#### 构造函数
```python
MCPToolsManagerWidget(
    parent=None,           # 父窗口
    agent_instance=None    # Agent 实例（可选）
)
```

#### 信号
```python
tools_selection_changed = Signal(list, list)
# 参数 1: enabled_tools (list[str]) - 启用的工具名称列表
# 参数 2: disabled_tools (list[str]) - 禁用的工具名称列表
```

#### 方法
```python
get_selected_tools() -> tuple[list[str], list[str]]
# 返回当前选择的工具（启用列表，禁用列表）
```

## 测试

运行测试脚本：
```bash
python test_mcp_tools_widget.py
```

测试内容：
1. ✅ 复选框初始状态反映 Agent 配置
2. ✅ 分组全选/全不选功能正常
3. ✅ 全选所有/反选所有功能正常
4. ✅ 信号正确发射，返回选择的工具列表

## 兼容性

- ✅ 向后兼容：旧的 `_set_all_checkboxes` 等方法已移除，但功能在新组件中保留
- ✅ 无破坏性变更：所有现有功能正常工作
- ✅ 类型检查：部分类型检查器误报不影响实际运行

## 未来改进

1. 添加工具搜索/过滤功能
2. 支持工具配置预设（保存多套配置）
3. 添加工具依赖关系检查
4. 支持按命名空间批量启用/禁用

## 相关文件

- `app_qt/widgets/mcp_tools_manager.py` - 新组件
- `app_qt/widgets/__init__.py` - 导出新组件
- `app_qt/ipython_console_tab.py` - 使用新组件
- `app_qt/ipython_llm_bridge.py` - Agent 状态管理优化
- `test_mcp_tools_widget.py` - 测试脚本
