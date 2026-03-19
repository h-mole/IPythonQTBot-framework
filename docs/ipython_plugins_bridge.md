# IPython 插件桥接使用指南

## 功能概述

IPython 插件桥接层允许你在 IPython 控制台中直接调用已加载的插件功能，所有调用都会在 UI 线程中安全执行并等待返回结果。

## 使用方法

### 1. 列出所有插件

```python
# 列出所有已加载的插件及其信息
plugins.list()
```

输出示例：
```
已加载的插件:
------------------------------------------------------------

插件名称：text_helper
版本号：1.0.0
描述：文本处理插件
作者：未知
可用方法：add_menu_to_menubar, register_text_action, get_text, set_text

------------------------------------------------------------
共 1 个插件
```

### 2. 查看插件详细信息

```python
# 查看指定插件的详细信息
plugins.info('text_helper')
```

### 3. 查看所有注册的方法

```python
# 查看所有插件的所有方法
plugins.methods()

# 查看指定插件的方法
plugins.methods('text_helper')
```

### 4. 调用插件方法

```python
# 调用 text_helper 插件的 get_text 方法
text = plugins.call.text_helper.get_text()

# 调用 text_helper 插件的 set_text 方法
plugins.call.text_helper.set_text("Hello World")

# 调用其他插件的方法（如果有的话）
# plugins.call.<plugin_name>.<method_name>(args...)
```

## 完整示例

### 示例 1：获取和设置文本

```python
# 获取当前文本处理标签页中的文本
current_text = plugins.call.text_helper.get_text()
print(f"当前文本：{current_text}")

# 设置新的文本
plugins.call.text_helper.set_text("这是新文本")
```

### 示例 2：批量处理文本

```python
# 获取当前文本
text = plugins.call.text_helper.get_text()

# 进行处理
processed = text.upper().replace(' ', '_')

# 设置处理后的文本
plugins.call.text_helper.set_text(processed)
```

### 示例 3：查看可用的插件

```python
# 查看所有插件
all_plugins = plugins.list()

# 遍历所有插件
for name, info in all_plugins.items():
    print(f"插件：{name}, 版本：{info['version']}")
```

## 技术细节

### UI 线程执行机制

所有的插件方法调用都会在 UI 主线程中执行，这是通过以下机制实现的：

1. **事件循环调度**：使用 `QTimer.singleShot(0, ...)` 将函数调用调度到主线程
2. **等待返回**：在处理事件循环的同时等待函数执行完成
3. **超时保护**：默认 5 秒超时，防止死锁

### 链式调用原理

`plugins.call.text_helper.get_text()` 的实现原理：

1. `plugins.call` 返回一个 `PluginCallWrapper` 对象
2. `.text_helper` 访问返回另一个包装器，记录插件名
3. `.get_text` 访问查找并包装实际的方法
4. `()` 调用触发包装的方法，在 UI 线程中执行

### 错误处理

- 如果插件未加载，会抛出 `AttributeError`
- 如果方法不存在，会抛出 `AttributeError`
- 如果执行超时（默认 5 秒），会抛出 `TimeoutError`
- 如果执行过程中发生异常，会抛出原始异常

## 注意事项

1. **必须在 IPython 控制台标签页中使用**：只有在 Qt 应用环境中才能正确执行
2. **避免长时间阻塞**：虽然调用在 UI 线程执行，但应尽量保持快速
3. **插件必须已加载**：只能调用已经加载的插件的方法
4. **方法必须已注册**：只能调用插件通过 `plugin_manager.register_method()` 注册的方法

## 支持的插件方法

每个插件可以注册多个公开方法，例如：

### text_helper 插件

- `get_text()` - 获取输入框文本
- `set_text(text)` - 设置输入框文本
- `add_menu_to_menubar(menu)` - 添加菜单到菜单栏
- `register_text_action(name, callback, shortcut)` - 注册自定义文本处理动作

## 调试技巧

```python
# 查看某个插件是否已加载
'text_helper' in plugins.list()

# 查看方法的返回值类型
result = plugins.call.text_helper.get_text()
print(type(result))

# 捕获异常
try:
    result = plugins.call.text_helper.non_existent_method()
except AttributeError as e:
    print(f"方法不存在：{e}")
except TimeoutError as e:
    print(f"执行超时：{e}")
```

## 高级用法

### 组合调用

```python
# 链式组合多个操作
text = plugins.call.text_helper.get_text()
plugins.call.text_helper.set_text(text.strip().upper())
```

### 条件执行

```python
# 根据条件执行不同操作
text = plugins.call.text_helper.get_text()
if len(text) > 100:
    plugins.call.text_helper.set_text(text[:100] + "...")
else:
    plugins.call.text_helper.set_text(text)
```

### 批处理

```python
# 批量处理多个操作
operations = [
    lambda: plugins.call.text_helper.set_text("第一步"),
    lambda: plugins.call.text_helper.set_text("第二步"),
    lambda: print("完成"),
]

for op in operations:
    op()
```
