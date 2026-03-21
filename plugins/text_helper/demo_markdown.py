"""
Markdown 渲染功能快速演示

运行此脚本将打开一个简单窗口，演示如何使用 Markdown 渲染功能。
"""
import sys
import os

# 设置环境变量（解决白屏问题）
os.environ['QT_OPENGL'] = 'software'
os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--disable-gpu'

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel
from PySide6.QtCore import Qt

# 尝试导入 QMarkdownView
try:
    from QMarkdownView import MarkdownView
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False
    print("警告：未安装 QMarkdownView，请运行：pip install qmarkdownview")


class MarkdownDemo(QWidget):
    """简单的 Markdown 渲染演示窗口"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Markdown 渲染演示")
        self.resize(1000, 700)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 标题
        title = QLabel("📝 Markdown 渲染演示 - 在左侧输入 Markdown，点击按钮预览")
        title.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        # 创建水平布局
        content_layout = QVBoxLayout()
        
        # 输入区域
        input_label = QLabel("输入 Markdown:")
        input_label.setStyleSheet("font-weight: bold;")
        content_layout.addWidget(input_label)
        
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("在此输入 Markdown 内容...")
        self.editor.setFontPointSize(11)
        content_layout.addWidget(self.editor)
        
        # 按钮区域
        btn_layout = QVBoxLayout()
        
        self.preview_btn = QPushButton("📄 预览 Markdown")
        self.preview_btn.setStyleSheet("padding: 10px; font-size: 14px;")
        self.preview_btn.clicked.connect(self.show_preview)
        btn_layout.addWidget(self.preview_btn)
        
        if not HAS_MARKDOWN:
            error_label = QLabel("⚠️  QMarkdownView 未安装，无法使用预览功能")
            error_label.setStyleSheet("color: red; padding: 10px;")
            btn_layout.addWidget(error_label)
        
        content_layout.addLayout(btn_layout)
        layout.addLayout(content_layout)
        
        # 预设示例内容
        self.load_example()
        
    def load_example(self):
        """加载示例 Markdown 内容"""
        example = """# 🎉 Markdown 示例

## 文本格式化

这是 **粗体**，这是 *斜体*，这是 `代码`

## 列表

### 无序列表
- 项目 1
- 项目 2
- 项目 3

### 有序列表
1. 第一步
2. 第二步
3. 第三步

## 代码块

```python
def greet(name):
    '''打招呼'''
    return f"Hello, {name}!"

print(greet("World"))
```

## 表格

| 功能 | 状态 | 评分 |
|------|------|------|
| 表格支持 | ✅ | ⭐⭐⭐⭐⭐ |
| 代码高亮 | ✅ | ⭐⭐⭐⭐⭐ |
| 目录生成 | ✅ | ⭐⭐⭐⭐ |

## 引用

> 生活就像一盒巧克力，
> 你永远不知道下一颗是什么味道。

## 任务列表

- [x] 安装 QMarkdownView
- [x] 打开演示程序
- [ ] 输入你的 Markdown 内容
- [ ] 点击预览按钮

---

**提示**: 点击 "📄 预览 Markdown" 按钮查看渲染效果！
"""
        self.editor.setPlainText(example)
    
    def show_preview(self):
        """显示 Markdown 预览"""
        if not HAS_MARKDOWN:
            print("请先安装：pip install qmarkdownview")
            return
        
        markdown_text = self.editor.toPlainText()
        
        if not markdown_text.strip():
            print("没有可渲染的内容")
            return
        
        # 创建预览对话框
        from PySide6.QtWidgets import QDialog, QHBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Markdown 预览")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        # 创建 Markdown 视图
        preview = MarkdownView()
        preview.setExtensions([
            "markdown.extensions.tables",
            "markdown.extensions.extra",
            "markdown.extensions.codehilite",
            "markdown.extensions.toc"
        ])
        preview.setValue(markdown_text)
        
        layout.addWidget(preview)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        dialog.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    demo = MarkdownDemo()
    demo.show()
    
    print("=" * 60)
    print("📝 Markdown 渲染演示")
    print("=" * 60)
    print("\n使用说明:")
    print("1. 在左侧编辑器中输入或修改 Markdown 内容")
    print("2. 点击 '📄 预览 Markdown' 按钮查看渲染效果")
    print("3. 在 text_helper 插件中也可以使用此功能 (Ctrl+Alt+M)")
    print("\n如果未安装 QMarkdownView，请先安装:")
    print("  pip install qmarkdownview")
    print("=" * 60)
    
    sys.exit(app.exec())
