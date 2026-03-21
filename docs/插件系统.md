# 插件系统设计文档

## 📋 概述

myhelper 插件系统是一个灵活的扩展框架，允许第三方开发者通过插件形式扩展应用功能。插件可以添加新的标签页、菜单项，并暴露方法供其他插件调用。

## 🏗️ 架构设计

### 核心组件

```
┌─────────────────────────────────────────────────────┐
│                   Main Window                       │
│  ┌───────────────┐  ┌────────────────────────────┐  │
│  │  Plugin       │  │   Built-in Tabs            │  │
│  │  Tabs         │  │   (TextHelper, IPython)    │  │
│  └───────────────┘  └────────────────────────────┘  │
│                       ↑                             │
│  ┌────────────────────┴──────────────────────────┐  │
│  │          Plugin Manager (单例)                 │  │
│  │  - 插件加载/卸载                               │  │
│  │  - 方法注册表                                  │  │
│  │  - 插件生命周期管理                            │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
           ↑                ↑
    ┌──────┴──────┐  ┌─────┴──────┐
    │ Plugin A    │  │ Plugin B   │
    │ quick_notes │  │ ...        │
    └─────────────┘  └────────────┘
```

### 目录结构

```
myhelper/
├── app_qt/
│   ├── plugin_manager.py         # 插件管理器核心
│   ├── main_window.py            # 主窗口（集成插件系统）
│   └── configs.py                # 配置（包含插件路径）
├── plugins/                       # 插件目录（启动路径下）
│   └── quick_notes/
│       ├── __init__.py
│       ├── plugin.json           # 插件配置文件
│       └── main.py               # 插件主模块
├── myhelper/                      # 数据目录（用户主目录下）
│   └── appcfg/
│       └── plugins_list.json     # 插件启用/禁用配置
└── docs/
    └── plugin_systems.md         # 本设计文档
```

## 🔌 插件开发规范

### 1. 插件配置文件 (plugin.json)

每个插件必须在其根目录包含 `plugin.json` 配置文件：

```json
{
  "name": "quick_notes",
  "description": "快速笔记插件 - 支持树状结构管理的笔记编辑器",
  "version": "1.0.0",
  "author": "Your Name",
  "main": "main",
  
  "dependencies": [
    {
      "name": "system:pandoc",
      "version": ">=2.0",
      "required": true,
      "description": "Pandoc 命令行工具"
    },
    {
      "name": "plugin:text_helper",
      "version": ">=1.0.0",
      "required": false,
      "description": "文本处理插件（可选依赖）"
    }
  ],
  
  "exports": {
    "namespace": "quick_notes",
    "description": "快速笔记核心 API",
    "methods": [
      {
        "name": "create_note",
        "description": "创建新笔记",
        "stable": true,
        "parameters": [
          {
            "name": "name",
            "type": "str",
            "description": "笔记名称",
            "required": true
          },
          {
            "name": "folder",
            "type": "str",
            "description": "所属文件夹路径（可选）",
            "required": false
          }
        ],
        "returns": {
          "type": "str",
          "description": "返回创建的笔记完整路径"
        }
      },
      {
        "name": "load_note",
        "description": "加载笔记内容",
        "stable": true,
        "parameters": [
          {
            "name": "path",
            "type": "str",
            "description": "笔记文件路径",
            "required": true
          }
        ],
        "returns": {
          "type": "str",
          "description": "返回笔记文本内容"
        }
      },
      {
        "name": "save_note",
        "description": "保存笔记",
        "stable": true,
        "parameters": [
          {
            "name": "path",
            "type": "str",
            "description": "笔记文件路径",
            "required": true
          },
          {
            "name": "content",
            "type": "str",
            "description": "笔记内容",
            "required": true
          }
        ],
        "returns": {
          "type": "bool",
          "description": "保存是否成功"
        }
      }
    ]
  },
  
  "callbacks": {
    "on_load": "load_plugin",
    "on_unload": "unload_plugin"
  },
  
  "tabs": [
    {
      "name": "📝 快速笔记",
      "class": "QuickNotesTab",
      "position": 2
    }
  ]
}
```

### 2. 插件入口文件 (main.py)

每个插件需要提供一个入口模块，包含加载和卸载函数：

```python
"""
Quick Notes Plugin - 快速笔记插件
"""
from PySide6.QtWidgets import QWidget

# 插件元数据
PLUGIN_NAME = "quick_notes"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "快速笔记插件 - 支持树状结构管理的笔记编辑器"


def load_plugin(plugin_manager):
    """
    插件加载入口函数
    
    Args:
        plugin_manager: 插件管理器实例
    
    Returns:
        dict: 包含插件组件的字典
    """
    print(f"[{PLUGIN_NAME}] 正在加载插件...")
    
    # 创建标签页实例
    notes_tab = QuickNotesTab()
    
    # 注册暴露的方法到全局域
    # 格式：plugin_manager.register_method(namespace, method_name, func)
    plugin_manager.register_method("quick_notes", "create_note", notes_tab.create_note_api)
    plugin_manager.register_method("quick_notes", "load_note", notes_tab.load_note_api)
    plugin_manager.register_method("quick_notes", "save_note", notes_tab.save_note_api)
    
    # 添加到标签页（由插件管理器统一管理）
    plugin_manager.add_plugin_tab("quick_notes", "📝 快速笔记", notes_tab, position=2)
    
    print(f"[{PLUGIN_NAME}] 插件加载完成")
    return {
        "tab": notes_tab,
        "namespace": "quick_notes"
    }


def unload_plugin(plugin_manager):
    """
    插件卸载回调
    
    Args:
        plugin_manager: 插件管理器实例
    """
    print(f"[{PLUGIN_NAME}] 正在卸载插件...")
    # 清理资源、保存状态等
    print(f"[{PLUGIN_NAME}] 插件卸载完成")
```

### 3. 接口稳定性规则

⚠️ **重要原则：插件暴露的方法一旦定义为 stable，就不可修改**

- **stable: true** - 稳定接口，任何修改都必须保持向后兼容
- **stable: false** - 实验性接口，可能在未来版本中变更或移除
- 如需重大变更，请创建新方法（如 `create_note_v2`），旧方法保留并标记为 deprecated

示例：
```json
{
  "methods": [
    {
      "name": "create_note",
      "stable": true,
      "deprecated": false,
      "description": "创建新笔记"
    },
    {
      "name": "create_note_advanced",
      "stable": false,
      "description": "创建高级笔记（实验性功能）"
    }
  ]
}
```

### 4. 依赖管理

插件可以通过 `dependencies` 字段声明依赖关系，支持两种类型的依赖：

#### 系统依赖

依赖外部系统工具（如 pandoc、git 等）：

```json
"dependencies": [
  {
    "name": "system:pandoc",
    "version": ">=2.0",
    "required": true,
    "description": "Pandoc 命令行工具，用于文档格式转换"
  }
]
```

#### 插件依赖

依赖其他插件提供的功能：

```json
"dependencies": [
  {
    "name": "plugin:text_helper",
    "version": ">=1.0.0",
    "required": false,
    "description": "文本处理插件（可选依赖）"
  }
]
```

#### 版本约束语法

支持多种版本约束格式：

- **精确匹配**: `"1.2.3"` - 必须是指定版本
- **大于等于**: `">=2.0"` - 2.0 及以上版本
- **小于等于**: `"<=3.0"` - 3.0 及以下版本
- **大于**: `">2.0"` - 严格大于 2.0
- **小于**: `"<3.0"` - 严格小于 3.0
- **脱字符**: `"^1.2.3"` - 允许 1.2.3 到 <2.0.0（主版本相同）
- **波浪符**: `"~1.2.3"` - 允许 1.2.3 到 <1.3.0（次版本相同）

#### 必需与可选依赖

- **required: true** - 必需依赖，不满足时插件无法加载
- **required: false** - 可选依赖，不满足时仅记录警告，插件仍可运行

#### 依赖检查时机

插件加载时会自动检查所有依赖：
1. 系统工具是否存在（通过 PATH 环境变量查找）
2. 系统工具版本是否满足要求
3. 依赖插件是否已加载
4. 依赖插件版本是否满足要求

依赖检查失败时，插件将不会加载，并输出详细的错误信息。

## 🔧 插件管理器 API

### PluginManager 核心方法

```python
class PluginManager:
    """插件管理器（单例模式）"""
    
    def get_instance():
        """获取单例实例"""
        pass
    
    def load_plugins():
        """加载所有启用的插件"""
        pass
    
    def register_method(namespace, method_name, func):
        """
        注册方法到全局域
        
        Args:
            namespace: 命名空间（通常为插件名）
            method_name: 方法名称
            func: 方法对象
        
        调用格式：plugin_manager.get_method("quick_notes.create_note")
        """
        pass
    
    def get_method(full_name):
        """
        获取已注册的方法
        
        Args:
            full_name: 完整方法名（格式："namespace.method_name"）
        
        Returns:
            function: 方法对象，不存在则返回 None
        """
        pass
    
    def add_plugin_tab(plugin_name, tab_name, tab_instance, position=None):
        """
        添加插件标签页
        
        Args:
            plugin_name: 插件名称
            tab_name: 标签页显示名称
            tab_instance: 标签页实例
            position: 插入位置（可选）
        """
        pass
    
    def add_plugin_menu(menu_name, menu_items):
        """
        添加插件菜单栏
        
        Args:
            menu_name: 菜单名称
            menu_items: 菜单项列表
        """
        pass
    
    def is_plugin_enabled(plugin_name):
        """检查插件是否已启用"""
        pass
    
    def get_all_methods():
        """获取所有已注册方法的列表"""
        pass
```

## 📝 插件启用/禁用配置

插件启用状态存储在 `~/myhelper/appcfg/plugins_list.json`：

```json
{
  "plugins": [
    {
      "name": "quick_notes",
      "enabled": true,
      "version": "1.0.0",
      "load_order": 1
    }
  ],
  "settings": {
    "auto_load_new_plugins": false,
    "allow_disable_builtin": false
  }
}
```

## 🎯 方法调用示例

### 在其他插件中调用 quick_notes 的方法

```python
def use_quick_notes(plugin_manager):
    """使用快速笔记插件的功能"""
    
    # 获取方法
    create_note = plugin_manager.get_method("quick_notes.create_note")
    save_note = plugin_manager.get_method("quick_notes.save_note")
    
    if create_note and save_note:
        # 创建笔记
        note_path = create_note(name="我的笔记", folder="工作")
        
        # 保存内容
        success = save_note(path=note_path, content="这是笔记内容")
        
        if success:
            print(f"笔记已保存：{note_path}")
```

## 🚀 插件加载流程

1. **扫描插件目录**: 遍历 `plugins/` 文件夹
2. **读取配置**: 加载每个插件的 `plugin.json`
3. **检查启用状态**: 从 `plugins_list.json` 读取配置
4. **按顺序加载**: 根据 `load_order` 加载启用的插件
5. **注册方法**: 执行 `load_plugin()` 注册暴露的方法
6. **添加 UI 组件**: 添加标签页和菜单项

## ⚠️ 注意事项

### 开发规范
- 插件名称必须唯一，使用小写字母和下划线
- 插件之间通过插件管理器提供的方法进行通信
- 不要直接依赖其他插件的模块，使用 `get_method()` 间接调用
- 插件应该独立运行，单个插件失败不应影响其他插件

### 错误处理
- 插件加载失败时记录日志但不影响其他插件
- 方法调用异常时返回 None 并记录错误信息
- 提供详细的加载日志便于调试

### 性能优化
- 插件按需加载，避免一次性加载过多插件
- 大型插件可以延迟初始化
- 缓存已注册的方法引用

## 📚 最佳实践

1. **保持接口简洁**: 一个插件专注于解决一类问题
2. **文档完善**: 在 `plugin.json` 中详细描述每个方法
3. **错误隔离**: 捕获并处理所有异常，避免影响主程序
4. **资源清理**: 在 `unload_plugin()` 中释放资源
5. **版本管理**: 使用语义化版本号 (major.minor.patch)

## 🔮 未来扩展

- 插件市场：在线下载和安装插件
- 热重载：运行时重新加载插件
- 权限系统：限制插件访问敏感功能
- 插件签名：验证插件来源和完整性

---

**最后更新**: 2026-03-19  
**版本**: 1.0.0
