"""
测试 Pandoc Utils 插件
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from app_qt.plugin_manager import PluginManager


def test_pandoc_utils_plugin():
    """测试 pandoc_utils 插件"""
    print("=" * 60)
    print("测试 Pandoc Utils 插件")
    print("=" * 60)

    # 创建 QApplication（必需）
    app = QApplication.instance() or QApplication(sys.argv)

    # 获取插件管理器实例
    pm = PluginManager.get_instance()

    # 加载插件
    pm.load_plugins()

    # 检查插件是否加载成功
    if pm.is_plugin_loaded("pandoc_utils"):
        print("\n✅ pandoc_utils 插件加载成功")

        # 获取插件信息
        plugin_info = pm.get_plugin_info("pandoc_utils")
        if plugin_info:
            print(f"   版本：{plugin_info.get('version', 'unknown')}")

        # 测试 API 方法
        print("\n测试 API 方法:")

        # 1. 测试 is_pandoc_available
        is_pandoc_available = pm.get_method("pandoc_utils.is_pandoc_available")
        if is_pandoc_available:
            is_available = is_pandoc_available()
            print(f"   - Pandoc 是否可用：{is_available}")

            if is_available:
                # 2. 测试 get_pandoc_version
                get_pandoc_version = pm.get_method("pandoc_utils.get_pandoc_version")
                if get_pandoc_version:
                    version = get_pandoc_version()
                    print(f"   - Pandoc 版本：{version}")

                # 3. 测试 convert_markdown_to_docx
                markdown_text = """# 测试文档

这是一个**测试**文档。

- 列表项 1
- 列表项 2
- 列表项 3

## 代码示例

```python
print("Hello, World!")
```
"""
                print("\n   - 测试 Markdown → DOCX 转换...")
                convert_md_to_docx = pm.get_method(
                    "pandoc_utils.convert_markdown_to_docx"
                )
                if convert_md_to_docx:
                    result = convert_md_to_docx(markdown_text=markdown_text)

                    if result and result.get("success"):
                        print(f"     ✅ 转换成功：{result.get('output_path')}")

                        # 4. 如果有成功的转换，测试反向转换
                        output_path = result.get("output_path")
                        if output_path and os.path.exists(output_path):
                            print("\n   - 测试 DOCX → Markdown 转换...")
                            convert_docx_to_md = pm.get_method(
                                "pandoc_utils.convert_docx_to_markdown"
                            )
                            if convert_docx_to_md:
                                reverse_result = convert_docx_to_md(
                                    docx_path=output_path
                                )

                                if reverse_result and reverse_result.get("success"):
                                    print(f"     ✅ 反向转换成功")
                                    markdown_content = reverse_result.get(
                                        "markdown", ""
                                    )
                                    if markdown_content:
                                        print(
                                            f"     Markdown 内容预览：{markdown_content[:100]}..."
                                        )
                                    else:
                                        print(f"     Markdown 内容为空")
                                else:
                                    error = (
                                        reverse_result.get("error", "未知错误")
                                        if reverse_result
                                        else "方法不存在"
                                    )
                                    print(f"     ❌ 反向转换失败：{error}")
                    elif result:
                        print(f"     ❌ 转换失败：{result.get('error', '未知错误')}")
                    else:
                        print(f"     ❌ 转换失败：方法不存在")
        else:
            print("   ⚠️  Pandoc 未安装，跳过功能测试")
            print("   提示：请安装 Pandoc (https://pandoc.org/installing.html)")

    else:
        print("\n❌ pandoc_utils 插件加载失败")
        print("   可能原因:")
        print("   1. 插件目录不存在")
        print("   2. plugin.json 配置错误")
        print("   3. 依赖不满足（需要 Pandoc）")

    # 打印所有注册的方法
    print("\n" + "=" * 60)
    print("已注册的方法:")
    all_methods = pm.get_all_methods()
    for method in sorted(all_methods):
        print(f"   - {method}")
    print("=" * 60)


if __name__ == "__main__":
    test_pandoc_utils_plugin()
