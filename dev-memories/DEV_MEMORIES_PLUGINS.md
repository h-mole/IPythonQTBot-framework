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

### 内置插件开发

#### 任务管理插件（daily_tasks）
**日期紧迫性颜色管理**（`plugins/daily_tasks/colors.py`）：
- 使用 `TaskColorManager` 类统一管理颜色
- 日期紧迫性分级：
  - `OVERDUE` - 已过期（浅红粉 #FECACA）
  - `TODAY` - 今日到期（鲜红 #EF4444 + 白字）
  - `WITHIN_3_DAYS` - 3天内（中等红 #FCA5A5）
  - `WITHIN_7_DAYS` - 7天内（浅粉红 #FFE4E6）
  - `NORMAL` - 正常（无特殊颜色）
  - `LONG_TERM/NO_DEADLINE` - 长期/无期限（浅紫 #E9D5FF）

**状态颜色**（与日期颜色独立）：
- 已完成：柔和绿 #BBF7D0
- 进行中：柔和黄 #FEF08A
- 已取消：浅灰 #E5E7EB
- 未开始：很浅蓝 #DBEAFE

**关键设计**：状态颜色和日期颜色分离，状态列始终显示状态颜色，日期列显示紧迫性颜色，避免同一状态显示不同颜色的问题。

**翻译注意事项**：任务完成状态、任务期限等固定名词，存储时都用英文，界面展示时候进行翻译。


#### 插件国际化（Plugin i18n）

**独立翻译系统**（`app_qt/plugin_i18n.py`）：
- 每个插件拥有独立的翻译域（domain）和 locale 目录
- 插件翻译文件位置：`plugins/{name}/locales/zh_CN/LC_MESSAGES/{name}.mo`
- 跟随主程序语言：通过 `get_i18n_manager().get_current_language()` 获取主程序当前语言
- 主程序切换语言时自动调用 `reload_all_plugins()` 刷新所有插件翻译

**插件实现要点**：
- 初始化 `PluginI18n(plugin_name, plugin_path)` 获取 `_` 函数
- 数据存储用英文（如状态 "Completed"），表格显示时通过 `tr_status()` 等映射函数翻译
- 筛选器按钮显示原始英文，表格单元格显示翻译后中文

**状态颜色兼容**：
- `TaskColorManager` 同时支持英文和中文状态键，兼容新旧数据

**翻译实现细节修复**（`plugins/daily_tasks/main.py`）：
- **表头翻译失效问题**：`COLUMNS` 作为全局或者类属性在类定义时就被翻译，此时插件翻译系统可能尚未初始化，导致翻译失效（显示英文）。解决：将表头定义移到 `init_ui()` 方法中作为局部变量，确保翻译系统已就绪后再进行翻译
- **筛选器按钮显示英文问题**：`MultiSelectFilter` 组件直接显示原始英文值。解决：为组件添加 `item_display_mapper` 参数（可选的显示文本映射函数），在 `show_menu()` 和 `update_button_text()` 中使用该函数翻译显示文本。状态筛选器传入 `tr_status`，分类筛选器传入 `tr_category`

**翻译文件维护工具**（`update_translations.py`）：
- 纯 Python 实现，无需外部 gettext 工具
- 功能：自动从 Python 代码提取 `_()`/`gettext()` 调用 → 合并到现有 .po 文件（保留已有翻译）→ 编译为 .mo 文件
- 支持主应用和所有插件的批量更新
- 使用：`python update_translations.py [--main|--plugins|--plugin NAME]`

---
