# Pandoc Utils Plugin

Pandoc 文档转换插件，提供 Markdown 与 DOCX 文档格式的互相转换功能。

## 功能特性

- ✅ Markdown → DOCX 转换
- ✅ DOCX → Markdown 转换
- ✅ 支持自定义 Word 模板
- ✅ 媒体文件自动提取
- ✅ Pandoc 版本检测

## 依赖要求

本插件需要系统安装 Pandoc：

### Windows 安装方式

```bash
# 使用 Chocolatey
choco install pandoc

# 使用 Scoop
scoop install pandoc

# 或从官网下载安装
# https://pandoc.org/installing.html
```

### 验证安装

```bash
pandoc --version
```

## API 接口

### convert_markdown_to_docx

将 Markdown 文本转换为 DOCX 文档。

```python
result = plugin_manager.get_method("pandoc_utils.convert_markdown_to_docx")(
    markdown_text="你的 Markdown 文本",
    template_path="path/to/template.docx",  # 可选
    output_dir="path/to/output"  # 可选
)

if result["success"]:
    print(f"转换成功：{result['output_path']}")
else:
    print(f"转换失败：{result['error']}")
```

### convert_docx_to_markdown

将 DOCX 文档转换为 Markdown 文本。

```python
result = plugin_manager.get_method("pandoc_utils.convert_docx_to_markdown")(
    docx_path="path/to/document.docx"
)

if result["success"]:
    print(result["markdown"])
else:
    print(f"转换失败：{result['error']}")
```

### is_pandoc_available

检查 Pandoc 是否可用。

```python
available = plugin_manager.get_method("pandoc_utils.is_pandoc_available")()
if available:
    print("Pandoc 可用")
else:
    print("Pandoc 未安装或不可用")
```

### get_pandoc_version

获取 Pandoc 版本号。

```python
version = plugin_manager.get_method("pandoc_utils.get_pandoc_version")()
if version:
    print(f"Pandoc 版本：{version}")
else:
    print("无法获取 Pandoc 版本")
```

## 使用方法

1. 在应用程序中切换到 "📝 Pandoc 转换" 标签页
2. 在左侧输入 Markdown 文本
3. 点击 "立即转换" 或使用快捷键 `Ctrl+Alt+M`
4. 转换成功后会自动打开输出目录

## 快捷键

- `Ctrl+Alt+M`: Markdown → DOCX
- `Ctrl+Alt+D`: DOCX → Markdown
- `Ctrl+Alt+T`: 选择模板文件
- `Ctrl+C`: 复制结果

## 注意事项

- 首次使用前请确保已安装 Pandoc
- 使用自定义模板时，请选择 `.docx` 格式文件
- 转换包含图片的文档时，图片会提取到输出目录的 `media` 子目录中
