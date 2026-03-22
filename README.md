# 快捷助手

## 技术栈
- **GUI 框架**: PySide6 (Qt for Python)
- **终端嵌入**: qtconsole (可选，用于高级 IPython 功能)
- **剪贴板管理**: pyperclip
- **IPython 支持**: ipython
- **LLM 集成**: openai (支持 Kimi、OpenAI、智谱等)

## 项目结构
```
myhelper/
├── app_qt/                      # PySide6 应用主目录
│   ├── __init__.py             # 应用入口
│   ├── main_window.py          # 主窗口（包含标签页管理）
│   ├── text_helper_tab.py      # 文本处理标签页
│   ├── ipython_console_tab.py  # IPython 控制台标签页
│   ├── ipython_plugins_bridge.py  # IPython 插件桥接
│   └── ipython_llm_bridge.py   # IPython LLM 对话框架
├── tabs/                        # Tkinter 版本标签页（保留）
│   ├── __init__.py
│   ├── ipython_tk.py
│   └── text_helper.py
├── helperscript.py             # Tkinter 版本主程序（保留）
├── run_helper.cmd              # Tkinter 版本启动脚本
├── run_helper_qt.py            # PySide6 Python 启动脚本
├── run_helper_qt.cmd           # PySide6 Windows 启动脚本
└── README.md
```

## 安装依赖
```bash
pip install PySide6 pyperclip ipython
```

可选（高级 IPython 功能）:
```bash
pip install qtconsole
```

## 运行方式

### PySide6 版本（推荐）
**Windows:**
```cmd
run_helper_qt.cmd
```

**跨平台:**
```bash
python run_helper_qt.py
```

### Tkinter 版本（旧版）
**Windows:**
```cmd
run_helper.cmd
```

**跨平台:**
```bash
python helperscript.py
```

## 功能特性

### 📝 文本处理
- 一键去除换行符
- 一键去除非法字符
- 去除文件名非法字符
- 复制结果到剪贴板
- 剪贴板历史记录（双击加载）
- 自动监控剪贴板更新

### 🔍 查找替换
- 查找文本
- 替换单个匹配项
- 全部替换
- 高亮显示匹配项

### 🐍 IPython 控制台
- 交互式 Python 代码执行
- 实时输出显示
- 错误信息追踪
- 清空输出功能
- **插件 API**: `plugins.list()`, `plugins.call.plugin_name.method()`
- **LLM 对话**: `agent.ask()`, `%agent_ask` 流式对话

## 新增功能：IPython LLM Agent

### 快速开始

1. **配置 API Key**
   ```bash
   # 在 .env 文件中配置
   API_KEY=your_kimi_api_key_here
   ```

2. **在 IPython 控制台中使用**
   ```python
   # 提问（流式输出）
   agent.ask("你好，请介绍一下自己")
   
   # 清除历史
   agent.clear()
   
   # 或使用 Magic 命令
   %agent_ask 什么是 Python 的装饰器？
   %agent_clear
   ```

### 主要特性
- ✅ 流式输出 - 实时显示 LLM 响应
- ✅ 历史记忆 - 自动保存对话上下文
- ✅ 多 LLM 支持 - Kimi、OpenAI、智谱等
- ✅ MCP 工具集成 - 自动调用启用的插件方法
- ✅ Magic 命令 - 便捷的命令行接口

详细文档：[docs/llm_agent_usage.md](docs/llm_agent_usage.md)

## 使用说明

1. **首次启动**: 程序会隐藏在系统托盘中，双击托盘图标打开主界面
2. **切换标签页**: 点击顶部标签切换不同功能
3. **剪贴板历史**: 在文本处理标签页右侧查看，双击可加载到编辑区
4. **退出程序**: 右键点击托盘图标，选择"退出程序"

## 注意事项

- PySide6 版本使用 Qt 框架，性能更好，界面更现代
- Tkinter 版本作为备选方案保留
- 建议安装 pyperclip 以获得更稳定的剪贴板支持
- IPython 功能需要额外安装 ipython 包
- 单独测试组件运行的脚本放在./single_component_tasks下面