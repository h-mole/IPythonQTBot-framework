# IPython 插件桥接层实现

## 概述

为 IPython 控制台添加了插件调用功能，允许在 IPython 中通过简单的 API 调用所有已加载的插件方法。

## 新增文件

1. **`app_qt/ipython_plugins_bridge.py`** - 核心桥接层实现
   - `PluginsAPI` - 主要 API 类
   - `PluginCallWrapper` - 插件调用包装器（支持链式调用）
   - `UIThreadExecutor` - UI 线程执行器
   - `execute_in_ui_thread()` - 在 UI 线程执行函数并等待结果

2. **`docs/ipython_plugins_bridge.md`** - 详细使用文档

3. **`test_ipython_bridge.py`** - 测试脚本

## 修改的文件

1. **`app_qt/ipython_console_tab.py`**
   - 添加 `_inject_plugins_api()` 方法
   - 在内核就绪时自动注入 `plugins` 对象到 IPython 命名空间

2. **`app_qt/main_window.py`**
   - 暂时注释掉 QuickNotesTab 导入（模块不存在）

## 功能特性

### 1. 列出所有插件
```python
plugins.list()
```

### 2. 查看插件信息
```python
plugins.info('text_helper')
```

### 3. 查看所有方法
```python
plugins.methods()
plugins.methods('text_helper')  # 查看指定插件的方法
```

### 4. 调用插件方法（重点功能）
```python
# 链式调用语法
text = plugins.call.text_helper.get_text()
plugins.call.text_helper.set_text("Hello World")

# 通用语法
plugins.call.<plugin_name>.<method_name>(args...)
```

## 技术亮点

### 1. UI 线程安全调用
- 所有插件方法调用都在 UI 主线程中执行
- 使用 `QTimer.singleShot(0, ...)` 调度到主线程
- 自动等待返回结果（带超时保护）
- 支持返回值和异常处理

### 2. 链式调用设计
- `plugins.call` → PluginCallWrapper
- `.text_helper` → 记录插件名
- `.get_text` → 查找并包装方法
- `()` → 触发执行

### 3. 动态方法发现
- 使用 `__getattr__` 实现动态属性访问
- 自动从 plugin_manager 获取已注册的方法
- 支持任意深度的链式调用

## 使用示例

### 在 IPython 控制台中

```python
# 1. 查看所有插件
>>> plugins.list()

# 2. 获取文本处理插件中的文本
>>> text = plugins.call.text_helper.get_text()
>>> print(text)

# 3. 设置文本
>>> plugins.call.text_helper.set_text("新文本")

# 4. 组合操作
>>> current = plugins.call.text_helper.get_text()
>>> plugins.call.text_helper.set_text(current.upper())
```

## 注意事项

1. **必须在 Qt 环境中运行** - 需要启动 GUI 应用后才能使用
2. **插件必须已加载** - 只能调用已加载且注册了方法的插件
3. **超时保护** - 默认 5 秒超时，防止 UI 卡死
4. **错误处理** - 插件/方法不存在会抛出 AttributeError

## 测试方法

### 1. 运行测试脚本
```bash
python test_ipython_bridge.py
```

### 2. 在实际应用中测试
```bash
python run_helper_qt.py
```

然后在 IPython 控制台标签页中输入：
```python
plugins.list()
plugins.call.text_helper.get_text()
```

## 扩展其他插件

其他插件只需在 `load_plugin()` 中注册方法即可被 IPython 调用：

```python
def load_plugin(plugin_manager):
    # 创建标签页
    tab = MyPluginTab()
    
    # 注册公开方法
    plugin_manager.register_method("my_plugin", "do_something", tab.do_something_api)
    
    return {"tab": tab, "namespace": "my_plugin"}
```

然后在 IPython 中就可以调用：
```python
plugins.call.my_plugin.do_something()
```

## 未来改进

- [ ] 添加方法参数提示
- [ ] 支持异步调用（不阻塞）
- [ ] 添加方法文档字符串显示
- [ ] 支持插件热重载
