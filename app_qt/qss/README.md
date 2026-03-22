# IPythonQTBot - 现代化样式表使用指南

## 📋 概述

本项目采用现代化的 UI 设计风格，提供统一的公共样式表和自定义标题栏组件，打造类似现代网站软件的用户体验。

## 🎨 设计特点

- **无边框窗口设计**：隐藏系统标题栏，使用自定义标题栏
- **扁平化设计**：简约、清爽的视觉效果
- **统一风格**：所有组件使用一致的配色和样式
- **响应式交互**：悬停、按下等状态有视觉反馈
- **现代配色**：使用蓝色系为主色调，搭配其他功能色

## 📁 文件结构

```
app_qt/
├── qss/                          # 样式表目录
│   ├── common.qss                # 公共样式表（主样式）
│   └── titlebar.qss              # 标题栏专用样式
├── widgets/                      # 组件目录
│   └── custom_titlebar.py        # 自定义标题栏组件
└── examples/                     # 示例代码
    └── style_demo.py             # 样式表演示程序
```

## 🚀 快速开始

### 1. 在主窗口中应用样式

```python
from PySide6.QtWidgets import QMainWindow
from app_qt.widgets.custom_titlebar import CustomTitleBar

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 设置为无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        # 加载样式表
        self._load_stylesheets()
        
        # 创建自定义标题栏
        self.title_bar = CustomTitleBar(
            parent=self,
            title="我的应用",
            icon="🚀"
        )
        
        # 添加到布局
        layout = QVBoxLayout()
        layout.addWidget(self.title_bar)
        self.centralWidget().setLayout(layout)
    
    def _load_stylesheets(self):
        """加载样式表"""
        import os
        qss_dir = os.path.join(os.path.dirname(__file__), 'qss')
        
        # 加载公共样式表
        with open(os.path.join(qss_dir, 'common.qss'), 'r', encoding='utf-8') as f:
            self.setStyleSheet(f.read())
        
        # 加载标题栏样式表
        with open(os.path.join(qss_dir, 'titlebar.qss'), 'r', encoding='utf-8') as f:
            self.setStyleSheet(self.styleSheet() + f.read())
```

### 2. 使用自定义标题栏

```python
# 基本用法
title_bar = CustomTitleBar(
    parent=self,
    title="应用标题",
    icon="🛠️"
)

# 带副标题的用法
title_bar = CustomTitleBar(
    parent=self,
    title="主标题",
    icon="📱",
    show_subtitle=True,
    subtitle="副标题或版本信息"
)
```

### 3. 应用预定义样式类

在公共样式表中定义了多种按钮样式：

```python
# 主要按钮（蓝色）
btn = QPushButton("主要按钮")
btn.setObjectName("primaryBtn")

# 成功按钮（绿色）
btn = QPushButton("成功按钮")
btn.setObjectName("successBtn")

# 危险按钮（红色）
btn = QPushButton("危险按钮")
btn.setObjectName("dangerBtn")

# 警告按钮（橙色）
btn = QPushButton("警告按钮")
btn.setObjectName("warningBtn")
```

## 🎯 样式复用

### 容器样式

```python
# 卡片式容器
card = QWidget()
card.setObjectName("cardWidget")

# 高亮容器
highlight = QWidget()
highlight.setObjectName("highlightWidget")

# 警告容器
warning = QWidget()
warning.setObjectName("warningWidget")

# 错误容器
error = QWidget()
error.setObjectName("errorWidget")

# 成功容器
success = QWidget()
success.setObjectName("successWidget")
```

### 标签样式

```python
# 大标题
title = QLabel("标题")
title.setObjectName("titleLabel")

# 副标题
subtitle = QLabel("副标题")
subtitle.setObjectName("subTitleLabel")

# 普通标签
label = QLabel("内容")
label.setObjectName("normalLabel")
```

### 输入框样式

```python
# 普通输入框
line_edit = QLineEdit()
# 自动应用公共样式

# 搜索输入框（圆角）
search_input = QLineEdit()
search_input.setObjectName("searchLine")
```

## 🎨 配色方案

### 主色调
- **主蓝色**: `#4a90e2` - 用于主要按钮、选中状态
- **深蓝色**: `#357abd` - 悬停状态
- **更深蓝**: `#2a5f8f` - 按下状态

### 功能色
- **成功绿**: `#4caf50` - 成功操作、确认按钮
- **危险红**: `#f44336` - 删除、关闭等危险操作
- **警告橙**: `#ff9800` - 警告、注意提示
- **中性灰**: `#e0e0e0` - 禁用状态、边框

### 背景色
- **主背景**: `#f8f9fa` - 窗口背景
- **卡片白**: `#ffffff` - 卡片容器背景
- **浅灰**: `#f5f5f5` - 分组框、标签页背景

## 📦 已集成的组件

以下组件已经应用了公共样式：

### IPython 控制台工具栏
- ✅ 清空按钮 (dangerBtn)
- ✅ 重启按钮 (primaryBtn)
- ✅ MCP 工具按钮 (warningBtn)
- ✅ 停止生成按钮 (warningBtn)

### 变量表格
- ✅ 标题标签 (subTitleLabel)
- ✅ 刷新按钮 (successBtn)
- ✅ 数据表格 (variablesTable)

### MCP 工具管理器
- ✅ 分组标签
- ✅ 复选框
- ✅ 按钮

## 🔧 自定义样式

如需为特定组件添加自定义样式，可以在公共样式表的基础上追加：

```python
# 方法 1：在组件中设置对象名，然后在 QSS 文件中添加样式
self.my_widget.setObjectName("myCustomWidget")

# 方法 2：直接追加特定样式
self.widget.setStyleSheet("""
    QWidget#myCustomWidget {
        background-color: #custom;
    }
""")
```

## 📝 最佳实践

1. **优先使用 objectName**：通过对象名应用样式，而不是内联样式
2. **复用公共样式**：能使用公共样式类的就不要重复定义
3. **保持一致性**：相同功能的元素使用相同的样式类
4. **避免硬编码**：颜色和尺寸尽量使用样式表统一管理
5. **测试多平台**：确保样式在不同操作系统上显示一致

## 🎭 动画效果

公共样式表包含了简单的过渡效果：

```css
QPushButton {
    transition: all 0.2s ease;  /* 平滑过渡 */
}
```

## 🖼️ 图标使用

建议使用 Unicode Emoji 作为图标：

- 🛠️ 工具
- 📊 图表
- 🔧 设置
- 🗑️ 删除
- 🔄 刷新
- ✅ 完成
- ❌ 错误
- ⚠️ 警告

## 📖 示例代码

运行样式演示程序查看效果：

```bash
cd app_qt
python examples/style_demo.py
```

## 🐛 常见问题

### Q: 为什么窗口无法拖动？
A: 确保使用了 `CustomTitleBar` 组件，它内置了窗口控制功能。

### Q: 样式不生效怎么办？
A: 检查是否正确设置了 `objectName`，并确保样式表已加载。

### Q: 如何修改主色调？
A: 编辑 `qss/common.qss` 文件中的颜色值，全局替换即可。

## 📚 参考资源

- [Qt 样式表语法](https://doc.qt.io/qt-6/stylesheet-syntax.html)
- [Qt 样式表参考](https://doc.qt.io/qt-6/stylesheet-reference.html)
- [QSS Skin Examples](https://github.com/ColinDuquesnoy/QDarkStyleSheet)

---

**最后更新**: 2026-03-22  
**维护者**: IPythonQTBot团队
