# MCP 工具管理功能

## 功能概述

为 IPython 控制台添加了 MCP 工具的启用/禁用管理功能，可以通过 GUI 界面或 API 接口来控制哪些 MCP 工具对 LLM Agent 可用。

## 主要特性

### 1. GUI 界面管理

在 IPython 控制台的顶部工具栏中新增了 **"🔧 MCP 工具"** 按钮，点击后会弹出管理对话框。

#### 对话框功能：

- **智能分组显示**：
  - 普通插件按命名空间分组（如 `quick_notes`、`text_helper`）
  - `mcp_bridge` 插件特殊处理：按双下划线前的子分组显示（如 `mcp_bridge.mcd-mcp`、`mcp_bridge.zhipu-mcp`）
- **命名空间全选/全不选**：每个分组都有一个复选框，可以一键启用/禁用该分组下的所有工具
- **单个工具控制**：可以单独勾选或取消某个具体工具
- **全选所有**：一键启用所有工具
- **反选所有**：反转当前所有工具的选择状态

### 2. API 接口

提供了支持 MCP 的系统方法，可以在 IPython 中直接调用：

```python
# 获取当前 MCP 工具的启用状态
status = system.get_mcp_tools_status()
print(status)
# 输出示例:
# {
#     "enabled": ["quick_notes.create_note", "text_helper.render_markdown"],
#     "disabled": ["email_utils.send_email"],
#     "total": 3
# }
```

### 3. Agent 集成

MCP 工具的选择会实时影响 LLM Agent 的可用工具列表：

- **过滤机制**：
  - 如果启用了过滤（设置了 enabled_tools），只有被选中的工具会对 Agent 可用
  - 被禁用的工具（disabled_tools）会从 Agent 的工具列表中移除
  - 如果没有设置任何过滤（默认情况），所有 `enable_mcp=True` 的工具都可用

- **动态更新**：在 GUI 中修改选择后，Agent 会立即重新构建工具列表，无需重启

## 使用方法

### 方法一：使用 GUI 界面

1. 启动应用后，打开 IPython 控制台标签页
2. 点击顶部工具栏的 **"🔧 MCP 工具"** 按钮
3. 在弹出的对话框中：
   - 使用命名空间复选框批量启用/禁用
   - 单独勾选需要的工具
   - 使用"全选所有"或"反选所有"快速操作
4. 点击"确定"保存设置

### 方法二：使用 API（在 IPython 中）

```python
# 查看当前状态
status = system.get_mcp_tools_status()
print(f"启用：{status['enabled']}")
print(f"禁用：{status['disabled']}")

# 手动更新过滤条件（通过 agent 实例）
agent.update_mcp_tools_filter(
    enabled_tools=["quick_notes.create_note", "text_helper.render_markdown"],
    disabled_tools=["email_utils.send_email"]
)

# 验证更新后的工具列表
tools = agent._build_mcp_tools()
print(f"当前可用工具数量：{len(tools)}")
```

## 实现细节

### 核心组件

1. **IPythonConsoleTab** (`ipython_console_tab.py`)
   - `show_mcp_tools_manager()`: 显示管理对话框
   - `_apply_mcp_tools_selection()`: 应用选择状态
   - `get_mcp_tools_status()`: 获取工具状态（MCP 接口）
   - **智能分组逻辑**：特殊处理 `mcp_bridge` 的 `mcd-mcp__xxxx` 格式，按双下划线前面的部分作为子分组

2. **Agent** (`ipython_llm_bridge.py`)
   - `update_mcp_tools_filter()`: 更新过滤条件
   - `_build_mcp_tools()`: 构建工具列表时应用过滤逻辑
   - `mcp_tools_enabled`: 启用的工具集合
   - `mcp_tools_disabled`: 禁用的工具集合

3. **PluginManager** (`plugin_manager.py`)
   - 提供 `get_all_methods(include_extra_data=True)` 获取所有 MCP 工具
   - 通过 `enable_mcp` 标识区分 MCP 工具

### 过滤逻辑

```python
# 在 Agent._build_mcp_tools() 中
for method_info in all_methods:
    # 只处理 enable_mcp=True 的方法
    if not extra_data.get('enable_mcp', False):
        continue
    
    # 检查是否在禁用列表中
    if method_name in self.mcp_tools_disabled:
        continue
    
    # 如果启用了过滤，只包含在启用列表中的工具
    if self.mcp_tools_enabled and method_name not in self.mcp_tools_enabled:
        continue
    
    # 添加到工具列表
    tools.append(tool_def)
```

## 注意事项

1. **初始状态**：默认情况下所有 MCP 工具都是启用的
2. **过滤优先级**：
   - 禁用列表优先于启用列表
   - 如果工具同时在启用和禁用列表中，它会被禁用
3. **空启用列表**：如果 `mcp_tools_enabled` 为空且 `mcp_tools_disabled` 也为空，表示不过滤，所有工具都可用
4. **性能考虑**：每次调用 `agent.ask()` 都会重新构建工具列表，建议在对话前完成配置

## 测试

运行测试脚本验证功能：

```bash
python test_mcp_tools_manager.py
```

测试内容包括：
- 扫描所有 MCP 工具
- 按命名空间分组
- 创建 IPython 控制台
- 获取工具状态

## 未来改进

- [ ] 保存用户的选择偏好到配置文件
- [ ] 添加搜索功能快速定位工具
- [ ] 显示工具的使用统计（调用频率）
- [ ] 支持导入/导出工具配置
- [ ] 添加工具依赖关系检查（禁用被依赖的工具时给出警告）
