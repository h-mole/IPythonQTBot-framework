---
name: example-skill
description: 这是一个示例技能，展示如何创建符合 agentskills-core 规范的技能。
  当你需要演示技能格式或学习创建新技能时参考此示例。
license: MIT
metadata:
  author: quick-notes-plugin
  version: "1.0"
  created: 2026-03-23
---

# 示例技能 - 如何创建技能

## 何时使用此技能

使用此技能作为参考模板来：
- 学习创建 agentskills-core 兼容的技能
- 了解 SKILL.md 文件的标准格式
- 快速开始创建你自己的技能

## 技能结构说明

### 必需元素

1. **YAML Frontmatter**
   ```yaml
   ---
   name: skill-name          # 必填：技能名称（kebab-case）
   description: 技能描述     # 必填：何时使用此技能
   ---
   ```

2. **Markdown 内容**
   - 清晰的标题
   - 使用时机说明
   - 执行步骤
   - 示例（推荐）

### 可选元素

- `scripts/` 目录：放置可执行脚本
- `references/` 目录：放置参考文档
- `assets/` 目录：放置模板和资源

## 创建步骤

### 第一步：确定技能名称

选择一个描述性的名称，使用 kebab-case 格式：
- ✅ `pdf-processing`
- ✅ `data-analysis`
- ❌ `PDF Processing`
- ❌ `data_analysis`

### 第二步：编写描述

描述应该清晰说明：
- 这个技能是做什么的
- 什么时候应该使用它
- 它能解决什么问题

示例：
```
description: 处理 PDF 文件，包括文本提取、表格分析和文档合并。
  当用户需要读取 PDF 内容、转换格式或处理扫描件时使用。
```

### 第三步：编写指令内容

指令应该包含：

1. **何时使用** - 明确的使用场景
2. **如何做** - 分步骤的执行指南
3. **示例** - 实际的输入输出示例
4. **注意事项** - 常见错误或特殊情况

### 第四步：添加支持文件（可选）

对于复杂的技能，可以添加：

```
my-skill/
├── SKILL.md
├── scripts/
│   └── process.py        # Python 脚本
├── references/
│   └── api-docs.md       # API 文档
└── assets/
    └── template.txt      # 模板文件
```

## 完整示例

以下是一个完整的 PDF 处理技能示例：

```markdown
---
name: pdf-processor
description: 处理 PDF 文件的各种操作，包括文本提取、格式转换和文档合并。
  当需要读取 PDF 内容、转换为其他格式或合并多个 PDF 时使用。
---

# PDF 处理技能

## 何时使用此技能

- 用户需要提取 PDF 中的文字
- 将 PDF 转换为 Word、Excel 等格式
- 合并多个 PDF 文件
- 分析 PDF 中的表格数据

## 如何处理 PDF

### 提取文本

1. 使用 `pdfplumber` 库打开 PDF
2. 遍历每一页提取文本
3. 保留基本的格式结构

```python
import pdfplumber

def extract_text(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    return text
```

### 转换格式

1. 确定目标格式（docx, xlsx, html）
2. 使用相应的转换工具
3. 验证转换结果

### 合并 PDF

1. 准备所有要合并的 PDF 文件
2. 按顺序添加到合并列表
3. 导出为新的 PDF 文件

## 示例

### 示例 1：提取文本

输入：`report.pdf`
输出：提取的文本内容

```bash
python scripts/extract.py report.pdf > output.txt
```

### 示例 2：合并 PDF

```python
from PyPDF2 import PdfMerger

merger = PdfMerger()
merger.append("file1.pdf")
merger.append("file2.pdf")
merger.write("combined.pdf")
```

## 常见问题

**Q: 扫描版 PDF 怎么处理？**
A: 需要使用 OCR 工具，如 pytesseract 或 Adobe Acrobat 的 OCR 功能。

**Q: 如何处理加密的 PDF？**
A: 需要先提供密码解密，可以使用 pypdf 库的 decrypt 方法。
```

## 验证你的技能

创建技能后，检查以下几点：

- [ ] SKILL.md 文件格式正确
- [ ] YAML frontmatter 包含必需的 name 和 description
- [ ] 技能名称符合 kebab-case 规范
- [ ] Markdown 内容结构清晰
- [ ] 提供了实际使用示例
- [ ] （如果有）脚本可以正常运行

## 下一步

创建技能后，你可以：

1. 在快速笔记的树状结构中查看它
2. 继续完善技能内容
3. 添加 scripts 和 references 目录
4. 分享给其他人使用

## 参考资料

- [Agent Skills 官方规范](https://learn.microsoft.com/en-us/agent-framework/agents/skills)
- [最佳实践指南](https://github.com/mgechev/skills-ref)
- [Skill 创建教程](https://blog.csdn.net/python12345_/article/details/157939874)
