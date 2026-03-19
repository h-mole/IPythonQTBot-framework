# IPython 插件桥接自动补全功能

## 功能概述

为 `plugins.call` 添加了智能自动补全支持，在 IPython 控制台中输入时可以获得实时的代码补全提示。

## 实现原理

通过实现 `__dir__()` 方法，动态返回可用的插件名称和方法列表：

```python
class PluginCallWrapper:
    def __dir__(self):
        """返回可用的插件名称列表，用于自动补全"""
        if self.plugin_name is None:
            # 在顶层时，返回所有已加载的插件名称
            return list(self.plugin_manager.loaded_plugins.keys())
        else:
            # 在插件层级时，返回该插件的所有方法
            methods = self.plugin_manager.methods_registry.get(self.plugin_name, {})
            return list(methods.keys())
```

## 使用效果

### 1. 插件名称补全

在 IPython 控制台中输入：

```python
>>> plugins.call.<TAB>
```

将显示所有已加载的插件名称，例如：

```
quick_notes
text_helper
pandoc_utils
```

### 2. 方法补全

选择插件后继续输入：

```python
>>> plugins.call.text_helper.<TAB>
```

将显示该插件的所有可用方法：

```
add_menu_to_menubar
get_text
register_text_action
set_text
```

### 3. 完整的补全流程

```python
# 第 1 步：输入 plugins.call. 后按 TAB
plugins.call.
# 提示：quick_notes, text_helper, pandoc_utils

# 第 2 步：选择 text_helper 后继续输入
plugins.call.text_helper.
# 提示：add_menu_to_menubar, get_text, register_text_action, set_text

# 第 3 步：选择 get_text 后调用
plugins.call.text_helper.get_text()
```

## 支持的 IDE/编辑器

此功能在所有支持 IPython/Jupyter 的环境中都能正常工作：

- ✅ **Jupyter Notebook / JupyterLab**
- ✅ **IPython 交互式控制台**
- ✅ **VS Code Python 扩展**
- ✅ **PyCharm 交互式控制台**
- ✅ **Spyder**

## 技术细节

### 动态属性发现

`__dir__()` 方法会在以下情况被调用：

1. 用户按下 TAB 键时
2. 使用 `dir()` 函数时
3. IDE/编辑器的智能提示功能

### 实时更新

补全列表是实时生成的，基于当前已加载的插件：

```python
# 如果插件在运行时被动态加载
>>> plugins.call.<TAB>  # 会显示新加载的插件

# 如果插件被卸载
>>> plugins.call.<TAB>  # 不再显示已卸载的插件
```

## 示例场景

### 场景 1：探索可用插件

```python
# 查看所有可用的插件
>>> dir(plugins.call)
['quick_notes', 'text_helper', 'pandoc_utils']

# 查看特定插件的方法
>>> dir(plugins.call.text_helper)
['add_menu_to_menubar', 'get_text', 'register_text_action', 'set_text']
```

### 场景 2：快速开发

```python
# 不需要记住具体的方法名
# 只需输入 plugins.call. 然后按 TAB 查看可用的插件
>>> plugins.call.text_helper.ge<TAB>
# 自动补全为
>>> plugins.call.text_helper.get_text()
```

### 场景 3：调试和探索

```python
# 在调试时快速查看可用的功能
>>> import pprint
>>> pprint.pprint(dir(plugins.call))
['quick_notes',
 'text_helper',
 'pandoc_utils']

>>> pprint.pprint(dir(plugins.call.text_helper))
['add_menu_to_menubar',
 'get_text',
 'register_text_action',
 'set_text']
```

## 注意事项

1. **插件必须已加载**：只有在插件管理器中已加载的插件才会出现在补全列表中
2. **方法必须已注册**：只有通过 `plugin_manager.register_method()` 注册的方法才会被补全
3. **实时性**：补全列表反映的是调用时的插件状态，不是静态的

## 修改的文件

- **`app_qt/ipython_plugins_bridge.py`**
  - `PluginCallWrapper.__dir__()` - 实现自动补全功能

## 测试方法

### 方法 1：运行测试脚本

```bash
python test_autocomplete.py
```

### 方法 2：在实际应用中测试

```bash
python run_helper_qt.py
```

然后在 IPython 控制台标签页中输入：

```python
plugins.call.<TAB>
plugins.call.text_helper.<TAB>
```

## 未来改进

- [ ] 添加方法签名提示（参数信息）
- [ ] 添加方法文档字符串显示
- [ ] 支持插件前缀过滤（如 `plugins.call.tex<TAB>` 只显示匹配的插件）
- [ ] 支持方法前缀过滤
