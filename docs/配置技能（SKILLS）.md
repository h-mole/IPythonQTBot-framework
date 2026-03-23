# 技能加载功能 - 快速开始

## 技能存储位置

- 技能存储于：

`~/IPythonQTBot/plugin_data/quick_notes/skills`

遵循标准的SKILLS.md格式。

## 技能创建

- 在“快速笔记”中，点击工具栏上方的“✨”按钮，即可弹出创建新技能的面板。配置后，完成后点击“创建”即可。

![点击上下文菜单中的创建命令](../pics/skills/create_skills_zh.png)

- 技能创建成功后，将显示以下对话框，并且左侧显示出技能配置文件：

![创建成功对话框](../pics/skills/create_skills_successdlg_zh.png)

![左侧显示技能配置文件](../pics/skills/view_skills_in_quick_notes_tree.png)

## 技能使用

### 获取全部技能

```markdown
In [1]: ask "请列出你当前的全部技能，对于一组嵌套的技能，只要说明下属的技能有多少个就可以了。"
------------------------------------------------------------
请求发起，等待处理...


思维过程:

用户要求列出我当前的全部技能，对于嵌套的技能，只要说明下属技能有多少个就可以了。我需要调用获取所有技能概要信息的工具。

输出结果:

我来获取您当前的技能列表。

工具调用过程:


Tool Call ID: tool-773dbb9640094f4aac2368546e9beba1Tool Call Function Name: call_quick_notes__get_all_skills_summary
Tool Call Function Arguments: {}


[系统] 检测到工具调用，正在处理...
[系统] 调用工具：call_quick_notes__get_all_skills_summary
[系统] 工具 call_quick_notes__get_all_skills_summary 
返回：[{'name': 'get-weather', 'type': 'skill', 'level': 0, 
'relative_path': 'get-weather', 'description':...


思维过程:

好的，我收到了技能列表。让我整理一下：

1. summary-webpage - 单独技能，用于总结网页

按照用户的要求，对于嵌套的技能，我只需要说明它有多少个子技能即可。

输出结果:

### 当前技能列表

| 技能名称 | 类型 | 描述 |
|---------|------|------|
| **summary-webpage** | 独立技能 | 读取网页信息并返回摘要 |
```

### 调用查询页面信息技能

````markdown
In [1]: ask 请查阅技能，运用技能里面的要求，帮我摘要这个网页：https://pypi.org/project/qtconsole/

> 注： 此时终端中将执行以下流程：

> 1. 从技能中查询到 `summary-webpage` 技能，描述是"读取网页信息，并且返回摘要"
> 2. 调用读取网页的MCP工具，获取网页结果
> 3. 创建最终输出

> 最终输出：

输出结果:

根据技能要求，我已经读取了网页内容，现在为您提供摘要：

### QtConsole 网页摘要

#### 项目基本信息
- 项目名称：qtconsole
- 最新版本：5.6.1
- 发布日期：2024年10月28日
- 项目描述：Jupyter Qt console

#### 核心功能
QtConsole 是一个基于 Qt 的富文本控制台，用于与 Jupyter 内核交互，主要特性包括：
- 富媒体输出支持
- 会话导出功能
- 内嵌图形显示
- 多行编辑与语法高亮
- 图形化调用提示
- 类似终端的轻量级体验

#### 安装方式

**方式一：使用 conda 安装（推荐）**
```bash
conda install qtconsole
```
conda 会自动安装 Qt 依赖

**方式二：使用 pip 安装**
```bash
pip install qtconsole
```
注意：pip 不会自动安装 Qt，需要手动安装：
```bash
pip install pyqt5
```

#### 使用方法
启动 QtConsole：
```bash
jupyter qtconsole
```

#### 系统要求
- Python 绑定：支持 PyQt6、PySide6、PyPy5 或 PySide2
- 平台支持：Windows、Linux、macOS

#### 项目状态
- 持续集成测试状态良好（Windows、macOS、Linux 均通过测试）
- 有完整的代码覆盖率报告
- 文档状态良好
- 有活跃的社区支持（Google Group）

#### 相关资源
- 项目文档提供最新版和稳定版 PDF 文档
- 通过 GitHub Issues 提供技术支持
- Jupyter Google Group 提供社区支持

#### 下载文件
- 源码分发包：qtconsole-5.6.1.tar.gz（435.8 kB）
- 构建分发包：qtconsole-5.6.1-py3-none-any.whl（125.0 kB）
````

## 技能格式解析
````markdown
---
name: [技能名称]
description: [技能描述（尽量1行以内）]
---

# 我的技能

## 何时使用

- 场景 1
- 场景 2

## 如何做

1. 步骤 1
2. 步骤 2

## 示例

```python
# 代码示例
```
````
