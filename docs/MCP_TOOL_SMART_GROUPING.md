# MCP 工具管理 - 智能分组改进

## 📋 改进背景

`mcp_bridge` 插件中的工具命名格式为 `mcp_bridge.mcd-mcp__xxxx`，如果按照普通的命名空间分组方式，所有的 `mcp_bridge` 工具都会显示在一个大组里，导致：

- 工具列表过长，难以浏览
- 无法批量管理不同的 MCP 服务器
- 用户难以找到需要的工具

## ✨ 改进内容

### 1. 智能分组逻辑

**修改文件**: `app_qt/ipython_console_tab.py`

```python
# 特殊处理 mcp_bridge 的格式：mcp_bridge.mcd-mcp__xxxx
# 需要按照双下划线前面的部分作为子分组
if namespace == 'mcp_bridge' and '__' in method_name:
    sub_group = method_name.split('__')[0]  # 例如：mcd-mcp
    group_key = f"{namespace}.{sub_group}"
else:
    group_key = namespace
```

### 2. 分组效果对比

#### 改进前 ❌
```
□ mcp_bridge (50 个工具)
  □ mcp_bridge.mcd-mcp__get_weather
  □ mcp_bridge.mcd-mcp__search_web
  □ mcp_bridge.zhipu-mcp__chat
  □ mcp_bridge.zhipu-mcp__translate
  ... (所有工具混在一起)
```

#### 改进后 ✅
```
□ mcp_bridge.mcd-mcp (25 个工具)
  □ mcp_bridge.mcd-mcp__get_weather
  □ mcp_bridge.mcd-mcp__search_web
  ...

□ mcp_bridge.zhipu-mcp (25 个工具)
  □ mcp_bridge.zhipu-mcp__chat
  □ mcp_bridge.zhipu-mcp__translate
  ...
```

### 3. 支持的分组类型

| 插件类型 | 分组依据 | 示例 |
|---------|---------|------|
| 普通插件 | 命名空间 | `quick_notes`, `text_helper` |
| mcp_bridge | 双下划线前的子分组 | `mcp_bridge.mcd-mcp`, `mcp_bridge.zhipu-mcp` |

## 🔧 技术实现

### 核心代码变更

**位置**: `ipython_console_tab.py` 的 `show_mcp_tools_manager()` 方法

```python
# 按命名空间分组（支持 mcp_bridge 的特殊格式）
namespace_groups = {}
for tool in mcp_tools:
    parts = tool['name'].split('.', 1)
    if len(parts) == 2:
        namespace = parts[0]
        method_name = parts[1]
        
        # 特殊处理 mcp_bridge 的格式
        if namespace == 'mcp_bridge' and '__' in method_name:
            sub_group = method_name.split('__')[0]
            group_key = f"{namespace}.{sub_group}"
        else:
            group_key = namespace
        
        namespace_groups[group_key].append(tool)
```

### 影响范围

1. **GUI 界面**: 对话框中的分组显示更清晰
2. **测试脚本**: `test_mcp_tools_manager.py` 同步更新
3. **文档**: 
   - `docs/mcp_tools_manager.md`
   - `docs/MCP_TOOL_QUICKSTART.md`

## 🎯 使用场景

### 场景 1: 管理多个 MCP 服务器

假设有多个 MCP 服务器：
- `mcd-mcp`: 微软 MCD 服务
- `zhipu-mcp`: 智谱 AI 服务
- `file-system`: 文件系统服务

**操作**:
1. 打开 MCP 工具管理器
2. 可以看到清晰的分组：`mcp_bridge.mcd-mcp`、`mcp_bridge.zhipu-mcp`、`mcp_bridge.file-system`
3. 可以单独启用/禁用某个服务器的所有工具

### 场景 2: 快速定位工具

**改进前**: 在 50+ 个工具的列表中滚动查找
**改进后**: 直接找到对应的 MCP 服务器分组，快速定位

### 场景 3: 调试特定 MCP 服务

当某个 MCP 服务器出现问题时：
1. 找到对应的分组（如 `mcp_bridge.problematic-mcp`）
2. 取消勾选该分组
3. 其他服务不受影响

## 📊 优势

| 方面 | 改进前 | 改进后 |
|-----|-------|-------|
| 分组数量 | 1 个大组 | 多个逻辑分组 |
| 可管理性 | 难以批量控制 | 可按 MCP 服务器批量管理 |
| 可读性 | 列表过长 | 结构清晰 |
| 扩展性 | 工具越多越难用 | 工具再多也清晰 |

## 🔄 向后兼容

- ✅ 不影响普通插件的分组逻辑
- ✅ 不影响 Agent 的过滤机制
- ✅ 不影响 API 接口调用
- ✅ 只改变 GUI 显示方式

## 🚀 未来优化方向

- [ ] 支持自定义分组规则（通过配置文件）
- [ ] 添加搜索功能快速定位工具
- [ ] 支持拖拽重新分组
- [ ] 显示每个 MCP 服务器的连接状态

## 📝 相关文档

- 详细文档：`docs/mcp_tools_manager.md`
- 快速指南：`docs/MCP_TOOL_QUICKSTART.md`
- 测试脚本：`test_mcp_tools_manager.py`

---

**更新日期**: 2026-03-22  
**影响文件**: 
- `app_qt/ipython_console_tab.py` (主要修改)
- `test_mcp_tools_manager.py` (测试同步)
- `docs/mcp_tools_manager.md` (文档更新)
- `docs/MCP_TOOL_QUICKSTART.md` (文档更新)
