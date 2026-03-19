"""
测试 Pandoc Utils 插件 - 验证菜单和模板功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from app_qt.plugin_manager import PluginManager


def test_pandoc_utils():
    """测试 Pandoc Utils 插件功能"""
    print("=" * 60)
    print("测试 Pandoc Utils 插件")
    print("=" * 60)

    # 创建应用实例
    app = QApplication(sys.argv)

    # 获取插件管理器
    plugin_manager = PluginManager.get_instance()

    # 加载所有插件
    plugin_manager.load_plugins()

    # 检查 pandoc_utils 是否加载成功
    if not plugin_manager.is_plugin_loaded("pandoc_utils"):
        print("❌ pandoc_utils 插件加载失败")
        return

    print("✅ pandoc_utils 插件加载成功")

    # 获取 pandoc_utils 的方法
    list_templates = plugin_manager.get_method("pandoc_utils.list_templates")
    set_template = plugin_manager.get_method("pandoc_utils.set_template")
    get_template_path = plugin_manager.get_method("pandoc_utils.get_template_path")
    convert_markdown_to_docx = plugin_manager.get_method(
        "pandoc_utils.convert_markdown_to_docx"
    )
    is_pandoc_available = plugin_manager.get_method("pandoc_utils.is_pandoc_available")

    # 测试 Pandoc 可用性
    print("\n测试 Pandoc 可用性...")
    if is_pandoc_available():
        print(
            f"✅ Pandoc 可用，版本：{plugin_manager.get_method('pandoc_utils.get_pandoc_version')()}"
        )
    else:
        print("⚠️  Pandoc 未安装或不可用")

    # 测试模板功能
    print("\n测试模板功能...")
    templates = list_templates()
    print(f"当前可用的模板：{templates}")

    if templates:
        # 选择第一个模板
        test_template = templates[0]
        print(f"\n尝试设置模板：{test_template}")
        success = set_template(test_template)
        if success:
            print(f"✅ 模板设置成功")
            current_path = get_template_path()
            print(f"当前模板路径：{current_path}")
        else:
            print(f"❌ 模板设置失败")

        # 清除模板
        print("\n清除模板...")
        set_template(None)
        current_path = get_template_path()
        if current_path is None:
            print("✅ 模板已清除")
        else:
            print(f"⚠️  模板未完全清除：{current_path}")
    else:
        print("ℹ️  暂无可用模板，请创建模板文件到以下目录:")
        print(
            f"   {os.path.join(os.path.expanduser('~'), '.myhelper', 'pandoc_utils', 'templates', 'docx')}"
        )

    # 测试转换功能
    print("\n测试转换功能...")
    test_markdown = """
# 测试文档

这是一个**测试**文档。

- 列表项 1
- 列表项 2
- 列表项 3

```python
print("Hello, World!")
```
"""

    result = convert_markdown_to_docx(test_markdown)
    if result.get("success"):
        print(f"✅ 转换成功！")
        print(f"输出路径：{result.get('output_path')}")
    else:
        print(f"❌ 转换失败：{result.get('error')}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_pandoc_utils()
