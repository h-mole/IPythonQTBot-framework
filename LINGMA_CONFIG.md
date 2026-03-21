# 通义灵码上下文配置

## 项目概述
- 项目名称：myhelper
- 主要功能：文本处理助手（Qt/PySide6 实现）
- 技术栈：Python + PySide6

## 项目结构说明
- `app_qt/` - Qt 主应用相关代码
- `tabs/` - 标签页功能模块
- `run_helper_qt.py` - Qt 版本入口脚本
- `requirements_qt.txt` - Qt 版本依赖

## 开发规范
- 变量命名：使用 camelCase
- 文本处理模式：统一使用原位替换模式
- UI 框架：PySide6

## 已知注意事项
- PySide6 的某些枚举值可能被 linter 误报，这是正常现象
- 避免剪贴板污染问题
- 使用原位替换时确保文本一致性
- 日志打印全部用logging.getLogger()来做,不使用print.
## 常用命令
- 使用的解释器：`venv`下面的虚拟环境
- 运行 Qt 版本：`python run_helper_qt.py`
- 安装依赖：`pip install -r requirements_qt.txt`

## 重要配置
- Shell: PowerShell (不支持 &&，需使用 ; 分隔语句)
- OS: Windows 22H2