# MCP 工具管理 - 快速开始

## 🎯 功能简介

通过 IPython 控制台工具栏的 **"🔧 MCP 工具"** 按钮，可以方便地管理哪些 MCP 工具对 LLM Agent 可用。

## 🚀 快速上手

### 1. 打开 MCP 工具管理器

启动应用后，在 IPython 控制台标签页的顶部工具栏找到并点击 **"🔧 MCP 工具"** 按钮。

### 2. 选择要启用的工具

在弹出的对话框中：
- ✅ **智能分组显示**：
  - 普通插件按命名空间分组（如 `quick_notes`、`text_helper`）
  - `mcp_bridge` 插件按子分组显示（如 `mcp_bridge.mcd-mcp`、`mcp_bridge.zhipu-mcp`）
- ✅ **分组全选框**：一键启用/禁用整个分组的工具
- ✅ **单个工具复选框**：精确控制每个工具的启用状态
- ✅ **全选所有**：启用所有 MCP 工具
- ✅ **反选所有**：反转当前选择

### 3. 应用设置

点击"确定"按钮，设置会立即生效，LLM Agent 的工具列表会自动更新。

## 💡 使用场景

### 场景 1: 减少干扰，只保留常用工具
```
1. 打开 MCP 工具管理器
2. 取消全选某些不常用的命名空间（如 email_utils）
3. 保留 quick_notes 和 text_helper 等核心工具
4. 点击确定
```

### 场景 2: 专注特定任务
```
假设你要写文档，只需要文档相关工具：
1. 打开 MCP 工具管理器
2. 只启用 pandoc_utils（文档转换）
3. 禁用其他无关工具
4. LLM 就不会被其他工具干扰
```

### 场景 3: 调试工具调用问题
```
当某个工具调用出错时：
1. 打开 MCP 工具管理器
2. 暂时禁用该工具
3. 测试其他工具是否正常
4. 定位问题后重新启用该工具
```

## 🔧 API 使用（高级）

在 IPython 控制台中，可以通过代码管理工具状态：

```python
# 查看当前状态
status = system.get_mcp_tools_status()
print(f"启用：{len(status['enabled'])} 个")
print(f"禁用：{len(status['disabled'])} 个")

# 手动设置过滤条件
agent.update_mcp_tools_filter(
    enabled_tools=["quick_notes.create_note"],
    disabled_tools=["email_utils.send_email"]
)

# 验证效果
tools = agent._build_mcp_tools()
print(f"当前可用工具：{len(tools)} 个")
for tool in tools:
    print(f"  - {tool['function']['name']}")
```

## ⚙️ 过滤规则

1. **默认状态**：所有 `enable_mcp=True` 的工具都可用
2. **禁用优先**：如果工具在禁用列表中，即使也在启用列表中也会被禁用
3. **启用过滤**：如果设置了启用列表（不为空），只有列表中的工具可用
4. **动态更新**：修改后立即生效，无需重启 Agent

## 📝 提示

- 工具数量较多时，建议使用分组管理
- `mcp_bridge` 的工具会自动按 MCP 服务器分组（如 `mcd-mcp`、`zhipu-mcp`）
- 可以多次打开管理器调整选择
- 修改会立即影响后续的 LLM 对话
- 当前的选择状态不会保存到配置文件（重启后恢复默认）

## ❓ 常见问题

**Q: 为什么我禁用了工具，LLM 还在尝试调用？**
A: 确保在修改后重新发起对话，因为工具列表是在每次 `agent.ask()` 时构建的。

**Q: 可以临时禁用某个工具吗？**
A: 可以，随时打开管理器取消勾选，用完后再启用即可。

**Q: 如何知道有哪些 MCP 工具？**
A: 打开管理器对话框可以看到所有已加载的 MCP 工具列表。
