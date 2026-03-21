"""
测试 Markdown 渲染功能
"""
import sys
import os

# 添加插件路径
plugin_path = os.path.join(os.path.dirname(__file__), '..', 'plugins', 'text_helper')
sys.path.insert(0, plugin_path)

# 测试导入
try:
    from main import TextHelperTab
    print("✓ 成功导入 TextHelperTab")
except Exception as e:
    print(f"✗ 导入失败：{e}")
    sys.exit(1)

# 测试组件创建
try:
    from PySide6.QtWidgets import QApplication
    
    # 创建应用
    app = QApplication([])
    
    # 创建标签页
    tab = TextHelperTab()
    print("✓ 成功创建 TextHelperTab 实例")
    
    # 测试设置文本
    test_markdown = """
# Hello World!

这是一个 **Markdown** 测试。

## 功能列表

- [x] 支持表格
- [x] 支持代码高亮
- [x] 支持目录

### 代码示例

```python
def hello():
    print("Hello, World!")
```

### 表格示例

| 姓名 | 年龄 | 城市 |
|------|------|------|
| 张三 | 25   | 北京 |
| 李四 | 30   | 上海 |
"""
    
    tab.set_text_api(test_markdown)
    print("✓ 成功设置 Markdown 文本")
    
    # 检查是否有 Markdown 渲染功能
    if hasattr(tab, 'show_markdown_preview'):
        print("✓ show_markdown_preview 方法存在")
    else:
        print("✗ show_markdown_preview 方法不存在")
    
    if hasattr(tab, 'render_markdown_api'):
        print("✓ render_markdown_api 方法存在")
    else:
        print("✗ render_markdown_api 方法不存在")
    
    # 检查 QMarkdownView 是否可用
    if hasattr(tab, 'HAS_MARKDOWN'):
        if tab.HAS_MARKDOWN:
            print("✓ QMarkdownView 可用")
        else:
            print("⚠ QMarkdownView 不可用，请安装 qmarkdownview 包")
    else:
        print("✗ HAS_MARKDOWN 属性不存在")
    
    print("\n测试完成！")
    print("\n使用方法:")
    print("1. 在文本处理插件中输入 Markdown 内容")
    print("2. 点击菜单 '📄 渲染 Markdown' 或按 Ctrl+Alt+M")
    print("3. 或者通过其他插件调用: text_helper.render_markdown()")
    
except Exception as e:
    print(f"✗ 测试失败：{e}")
    import traceback
    traceback.print_exc()
