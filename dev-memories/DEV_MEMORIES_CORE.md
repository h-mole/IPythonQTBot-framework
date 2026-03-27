# 上下文配置

> **如何更新该文件**
> 
> 1. **按模块组织**：每个技术模块独立成节，本节只记录与该模块直接相关的开发经验
> 2. **留空规则**：如果某次开发不涉及某模块，保持该模块为 `（暂无内容）` 或留空
> 3. **新增模块**：如需新增模块，在"模块分节"区域添加，遵循相同格式
> 4. **经验格式**：每条经验应包含「场景-问题-解决方案」或「最佳实践说明」
> 5. **及时更新**：完成一个功能/修复一个bug后，应立即将关键经验写入对应模块；如果有不正确的内容，请及时更正为和代码实现逻辑一致的内容。
> 6. **避免冗余**：不写显而易见的内容（如"Python 用 print 输出"），只写容易遗忘的技术细节
> 7. **及时删除**: 如果有过时内容，请更新完本文件的同时，删除之前过时的内容，避免影响开发。
> 8. **内容精炼**: 多用简练的自然语言、代码标识符，不要直接贴代码实现，保持文档简洁。

---

## 项目概述
- 项目名称：IPythonQTBot
- 主要功能：文本处理助手（Qt/PySide6 实现）
- 技术栈：Python + PySide6

## 项目结构说明
- `app_qt/` - Qt 主应用相关代码
- `plugins/` - 插件目录
- `app_qt/qss/` - QSS 样式文件目录
- `run_helper_qt.py` - Qt 版本入口脚本
- `requirements.txt` - 项目依赖

## 模块分节

### QSS 样式系统

#### 核心原则
- **Qt QSS 不支持 CSS 变量**：不能使用 `--color-primary` 或 `var()` 语法，必须使用直接颜色值（如 `#2563EB`）
- **加载顺序至关重要**：后加载的样式会覆盖先加载的相同样式
  - 推荐顺序：`common.qss`（基础）→ `colors.qss`（组件类）→ `titlebar.qss` → `dark_theme.qss`（主题覆盖）

#### 组件样式类（cssClass）使用规范
定义在 `app_qt/qss/colors.qss` 中，通过 `setProperty("cssClass", "类名")` 使用：

| 类名 | 用途 | 颜色 |
|------|------|------|
| `btn-primary` | 主操作按钮 | 蓝色 #2563EB |
| `btn-success` | 成功/确认按钮 | 绿色 #16A34A |
| `btn-warning` | 警告/注意按钮 | 琥珀色 #F59E0B |
| `btn-danger` | 危险/删除按钮 | 红色 #EF4444 |
| `btn-info` | 信息按钮 | 青色 #06B6D4 |
| `btn-secondary` | 次要/幽灵按钮 | 透明背景+边框 |
| `status-idle` | 空闲状态标签 | 灰色背景 |
| `status-running` | 运行中状态 | 绿色背景+白字 |
| `status-completed` | 完成状态 | 蓝色背景+白字 |
| `status-warning` | 警告状态 | 琥珀色背景+白字 |
| `status-error` | 错误状态 | 红色背景+白字 |
| `info-badge` | 信息徽章（如Token计数） | 白底+边框 |
| `container-primary/success/warning/danger/info` | 高亮容器背景 | 对应浅色背景 |

#### 动态切换样式类
运行时切换控件的 cssClass（如状态标签），需要调用 `style().unpolish()` 和 `style().polish()` 刷新样式。

#### 深色主题实现
- 深色样式在 `dark_theme.qss` 中定义
- 通过**完全覆盖**相同样式选择器实现切换，而非 CSS 变量
- 深色主题颜色使用更高亮度/饱和度的颜色（如 `#60A5FA` 代替 `#2563EB`），以在深色背景上保持可读性

#### 主题管理器（ThemeManager）
位于 `app_qt/widgets/theme_manager.py`，单例模式。主要 API：
- `get_theme_manager()` - 获取实例
- `apply_theme(app, "light"/"dark")` - 应用主题
- `toggle_theme(app)` - 切换主题
- `reload_theme(app, theme_name)` - 强制刷新（开发时用）

#### 菜单中的主题切换
- 使用 `QActionGroup` 并设置 `setExclusive(True)` 实现互斥选择
- 使用 `blockSignals()` 在更新选中状态时防止触发不必要的信号
- 通过 `QActionGroup.triggered` 信号统一处理，避免直接用 `triggered.connect(lambda)`

#### qtconsole 主题支持
`RichJupyterWidget` 有自己的样式系统：
- `style_sheet` 属性 - 控制控件外观（背景色、文字色等）
- `syntax_style` 属性 - 控制语法高亮主题
  - 浅色主题推荐：`"default"`
  - 深色主题推荐：`"monokai"`
  - 其他可用：`solarized-dark`, `solarized-light`, `vim` 等

#### 深色主题菜单样式注意事项
`dark_theme.qss` 中需要为 `QMenu::item` 明确定义默认文字颜色 `color: #F5F5F5`，否则可能继承为深色导致看不清。

#### 深色主题边框与文字颜色最佳实践
- **card 边框颜色**：使用 `#404040`（比 `#525252` 更淡），避免边框过于突兀
- **card 文字颜色**：使用 `#E5E5E5`（比 `#F5F5F5` 稍柔和但仍清晰），确保可读性
- **分组框边框**：同样使用 `#404040` 保持一致性

#### 自定义复选框（CustomCheckBox）样式控制
位于 `app_qt/widgets/custom_checkbox.py`：
- **禁止硬编码颜色**：不在代码中设置 `setStyleSheet("color: #333333")`，否则深色主题下会看不清
- **完全由 QSS 控制**：在 `common.qss`（浅色）和 `dark_theme.qss`（深色）中分别定义 `CustomCheckBox QLabel` 的颜色
- **悬停效果**：通过 `CustomCheckBox:hover QLabel` 在 QSS 中定义，而非代码中的 `eventFilter`

#### QComboBox 下拉列表深色样式
`QComboBox QAbstractItemView` 需要完整定义 `background-color` 和 `color`，否则下拉列表可能显示为系统默认白色背景：
```css
QComboBox QAbstractItemView {
    background-color: #262626;
    color: #F5F5F5;
}
QComboBox QAbstractItemView::item {
    background-color: #262626;
    color: #F5F5F5;
}
```

#### QComboBox 自定义下拉箭头
使用 `image: url(path/to/icon.svg)` 设置 SVG 箭头图标：
```css
QComboBox::down-arrow {
    image: url(app_qt/icons/down-triangle.svg);
    width: 12px;
    height: 12px;
}
```
注意：Qt QSS 的 `image` 属性支持 SVG，但无法通过 QSS 动态修改 SVG 颜色。如需不同主题使用不同颜色，需准备多个 SVG 文件或使用 CSS border 技巧绘制箭头。

#### 主题切换后样式刷新
Qt 样式表有缓存，切换主题后必须手动刷新才能生效。关键步骤：
1. 调用 `widget.style().unpolish()` 清除旧样式缓存
2. 调用 `widget.style().polish()` 应用新样式
3. 调用 `widget.update()` 触发重绘
4. 递归处理所有子控件

#### ThemeManager 缓存与状态一致性
`load_theme()` 方法会缓存已加载的主题样式。**重要**：`current_theme` 状态必须在每次调用时更新，即使在缓存命中时也要更新，否则会导致菜单选中状态与实际主题不一致的 bug。

#### 语法高亮编辑器（SyntaxEdit）
位于 `plugins/quick_notes/syntaxedit/`，基于 `QTextEdit` + Pygments 实现：

**背景色跟随 QSS 主题**：
- 不设置内联样式表，让背景色完全由 QSS 控制（避免覆盖 QSS 样式）
- 通过 `get_theme_manager().get_current_theme()` 获取当前主题
- 使用硬编码颜色映射 `THEME_COLORS` 确保 HTML 背景色与 QSS 一致

**深色/浅色不同高亮方案**：
- 浅色主题：`default` 方案（深色文字，适合白底）
- 深色主题：`monokai` 方案（亮色文字，适合黑底）
- 通过 `_pygments_theme_light` 和 `_pygments_theme_dark` 配置

**去除边框留白**：
- `setViewportMargins(0, 0, 0, 0)` - 去除视口边距
- `document().setDocumentMargin(0)` - 去除文档边距
- 防止深色主题下出现亮色边框

**HTML 填满编辑器**：
- 生成的 HTML 使用 `<html><body style="background-color: {bg}">` 确保背景色填满
- 防止短文本时编辑器下方出现白色空白

**防抖渲染机制**：
- 使用 `QTimer` 实现 500ms 防抖（`DEBOUNCE_INTERVAL = 500`）
- 连续输入时只会在停止输入 500ms 后渲染一次，避免卡顿
- `flush()` 方法用于立即刷新（如主题切换时）

**首次立即高亮**：
- 初始化时使用 `_initialHighlight()` 立即高亮，不等待防抖定时器
- 确保文本打开时立即可见高亮效果

**注意**：`setStyleSheet()` 会覆盖 QSS 样式，导致深色主题失效，因此完全依赖 QSS 控制背景色。

#### CollapsibleGroup 组件样式
位于 `app_qt/widgets/collapsible_group.py`：

**移除硬编码样式**：
- Header 背景色、标签颜色等不再使用 `setStyleSheet()`
- 改用 `setProperty("cssClass", "card")` 让 QSS 控制样式

**深色主题适配**：
- `dark_theme.qss` 中为 `QWidget[cssClass="card"] QLabel` 定义 `color: #F5F5F5`
- 确保卡片内的文字在深色背景下清晰可见

**自定义展开/折叠箭头**：
- 使用 `QLabel` + `QPixmap` 加载 `app_qt/icons/down-triangle.svg` 替代 `QToolButton` 的默认箭头
- 通过 `QTransform().rotate(270)` 实现折叠状态（向右）、展开状态（向下）的图标切换
- 优点：SVG 图标样式统一，可随主题更换颜色（通过不同 SVG 文件）

---

### UI 控件开发

#### 状态标签最佳实践
不要硬编码样式表，使用 QSS 类。通过 `setProperty("cssClass", "类名")` 设置样式类，然后调用 `style().unpolish()` 和 `style().polish()` 刷新。

---

### 开发环境与工具

#### 常用命令
- 使用的解释器：`venv` 下面的虚拟环境
- 运行 Qt 版本：`python run_helper_qt.py`
- 安装依赖：`pip install -r requirements.txt`

#### 环境配置
- Shell: PowerShell (不支持 `&&`，需使用 `;` 分隔语句)
- OS: Windows 22H2

---

### 代码规范

- 变量命名：使用小写+下划线，除了pyside固有接口使用camelCase之外
- 文本处理模式：统一使用原位替换模式
- UI 框架：PySide6
- 日志打印：全部用 `logging.getLogger()`，不使用 `print`

#### 已知注意事项
- PySide6 的某些枚举值可能被 linter 误报，这是正常现象
- 避免剪贴板污染问题
- 使用原位替换时确保文本一致性

---

### 6. 数据处理
（暂无内容）

---

### 7. 网络通信
（暂无内容）

---

### 8. 国际化 (i18n)

位于 `app_qt/i18n.py`，采用 gettext 风格实现：

**核心组件**：
- `I18nManager` - 单例管理器，维护当前语言状态
- `install_translator()` - 加载 .mo 翻译文件
- `_()` - 全局翻译函数

**语言检测优先级**：
1. 显式传入参数
2. 配置文件 `settings.language.language`（auto/en/zh_CN）
3. 系统区域（zh 开头用中文，其他用英文）

**PO/MO 文件**：
- 源文件：`app_qt/locales/zh_CN/LC_MESSAGES/messages.po`
- 编译后：`.mo` 文件
- **关键**：.mo 文件必须包含 UTF-8 字符集头部，否则中文解码失败
- 文件格式：MO 文件头 + 原始字符串表 + 翻译字符串表 + 字符串数据

**Qt 翻译器**：
- 同时安装 `QTranslator` 用于 Qt 内置字符串（如对话框按钮）
- Qt 翻译文件路径：`qt_{lang}.qm`

---

### 9. 性能优化
（暂无内容）

---

## 附录：颜色速查表

本速查表需要保持和QSS一致，如果有修改QSS，则需要及时更新。

### 浅色主题色板
| 用途 | 颜色值 | 说明 |
|------|--------|------|
| Primary-600 | #2563EB | 主按钮 |
| Primary-500 | #3B82F6 | 滑块/进度条 |
| Success-600 | #16A34A | 成功按钮 |
| Warning-500 | #F59E0B | 警告按钮 |
| Danger-500 | #EF4444 | 危险按钮 |
| Info-500 | #06B6D4 | 信息按钮 |
| Neutral-200 | #E5E7EB | 边框/分隔线 |
| Neutral-100 | #F5F5F5 | 背景 |

### 深色主题色板
| 用途 | 颜色值 | 说明 |
|------|--------|------|
| Primary-400 | #60A5FA | 主按钮（深色用更亮的蓝）|
| Success-400 | #4ADE80 | 成功按钮 |
| Warning-400 | #FBBF24 | 警告按钮 |
| Danger-400 | #F87171 | 危险按钮 |
| Bg-Primary | #262626 | 卡片背景 |
| Bg-Secondary | #171717 | 全局背景 |
| Text-Primary | #F5F5F5 | 主文字 |
