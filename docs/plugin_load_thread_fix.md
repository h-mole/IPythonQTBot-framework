# 插件加载线程问题修复

## 问题描述

在加载 quick_notes 插件时出现以下错误：

```
QObject::setParent: Cannot set parent, new parent is in a different thread
```

这导致快速笔记插件无法正常加载。

## 问题原因

Qt 的 GUI 组件（如 QWidget、QTabWidget 等）必须在主线程（GUI 线程）中创建和操作。当插件标签页在非主线程中创建并尝试添加到主线程的 QTabWidget 时，会出现跨线程设置父对象的错误。

## 解决方案

将插件加载过程移回主线程执行，确保所有 UI 操作都在主线程中完成。

### 修改的文件

1. **`app_qt/main_window.py`**
   - 添加 `_load_plugins_before_ui()` 方法
   - 在 `__init__()` 中先调用插件加载，再创建 UI
   - 在 notebook 创建后更新插件管理器的引用

2. **`app_qt/ipython_console_tab.py`**
   - 注释说明 `_inject_plugins_api()` 在主线程中执行

### 关键改动

#### main_window.py

```python
def __init__(self):
    super().__init__()
    
    # 窗口设置
    self.setWindowTitle("快捷助手")
    self.setGeometry(100, 100, 900, 600)
    
    # 剪贴板历史记录
    self.clipboard_history = []
    self.max_clipboard_history = 50
    
    # 先加载插件（在主线程中）- 新增
    self._load_plugins_before_ui()
    
    # 创建界面组件
    self.create_widgets()
    
    # 系统托盘
    self.tray_icon = None
    self.create_tray()

def _load_plugins_before_ui(self):
    """在创建 UI 之前加载插件（确保在主线程中）"""
    try:
        from app_qt.plugin_manager import get_plugin_manager
        
        # 获取插件管理器实例
        plugin_manager = get_plugin_manager()
        
        # 设置主窗口引用（此时 notebook 还未创建）
        plugin_manager.set_main_window(self, None, None)
        
        # 加载所有插件（在主线程中）
        plugin_manager.load_plugins()
        
        print("[MainWindow] 插件预加载完成")
        
    except Exception as e:
        print(f"[MainWindow] 插件预加载失败：{e}")
        import traceback
        traceback.print_exc()
```

#### 在 create_widgets() 中更新 notebook 引用

```python
# 创建标签页控件
self.notebook = QTabWidget()
main_layout.addWidget(self.notebook)

# 更新插件管理器的 notebook 引用（此时已创建）
from app_qt.plugin_manager import get_plugin_manager
plugin_manager = get_plugin_manager()
plugin_manager.set_main_window(self, self.notebook, None)
```

## 执行流程

1. **主窗口初始化** → `QuickAssistant.__init__()`
2. **预加载插件** → `_load_plugins_before_ui()`
   - 获取插件管理器单例
   - 设置主窗口引用（notebook=None）
   - 在主线程中加载所有插件
   - 插件创建的标签页加入待处理队列
3. **创建 UI** → `create_widgets()`
   - 创建 notebook 控件
   - 更新插件管理器的 notebook 引用
   - 插件管理器将待处理的标签页添加到 notebook
4. **IPython 控制台初始化**
   - 启动内核线程
   - 内核就绪后注入 plugins API（在主线程回调中）

## 优点

1. ✅ **线程安全**：所有 UI 操作都在主线程中执行
2. ✅ **简单清晰**：不需要复杂的线程同步机制
3. ✅ **提前加载**：插件在 UI 显示前已加载完成，用户体验更好
4. ✅ **错误避免**：完全避免了跨线程操作 Qt 对象的问题

## 注意事项

- 插件加载是同步阻塞的，如果插件加载时间过长会影响启动速度
- 对于耗时的初始化操作（如网络请求、文件读写），建议在插件内部使用异步方式
- IPython 内核仍然在独立线程中运行，但 API 注入是在主线程回调中执行的

## 测试验证

运行程序后，所有插件正常加载：

```
[PluginManager] 开始加载插件...
[PluginManager] 正在加载插件：quick_notes v1.0.0
[QuickNotes] 正在加载快速笔记插件...
[PluginManager] 注册方法：quick_notes.create_note
[PluginManager] 注册方法：quick_notes.load_note
[PluginManager] 注册方法：quick_notes.save_note
[PluginManager] notebook 未初始化，标签页 📝 快速笔记 已加入待处理队列
[QuickNotes] 快速笔记插件加载完成
[PluginManager] 插件 quick_notes 加载成功
...
[MainWindow] 插件预加载完成
[PluginManager] 已添加插件标签页：📝 快速笔记 (插件：quick_notes)
[PluginManager] 已添加插件标签页：📝 文本处理 (插件：text_helper)
```

没有出现线程错误，所有插件标签页正常显示。✅
