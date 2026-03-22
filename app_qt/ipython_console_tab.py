"""
IPython 控制台标签页 - PySide6 版本
使用 qtconsole.rich_jupyter_widget.RichJupyterWidget
需要安装：pip install ipython qtconsole
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QGroupBox,
    QSplitter,
    QHBoxLayout,
    QPushButton,
    QToolBar,
)
from PySide6.QtGui import QFont, QIcon, QKeyEvent
from PySide6.QtCore import QThread, Signal, Qt
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager
import logging
import sys
from app_qt.plugin_manager import get_plugin_manager
from IPython.utils.capture import capture_output

# 导入变量表格组件
from .widgets.variables_table import VariablesTable

# 导入 MCP 工具管理器组件
from .widgets.mcp_tools_manager import MCPToolsManagerWidget
from IPython.display import display, Markdown

logger = logging.getLogger(__name__)


class KernelInitThread(QThread):
    """内核初始化线程"""

    kernel_ready = Signal(object)  # 发射 kernel_manager
    error_occurred = Signal(str)  # 发射错误信息

    def __init__(self):
        super().__init__()
        self.kernel_manager = None

    def run(self):
        """在线程中初始化内核"""
        try:
            # 创建内核管理器
            self.kernel_manager = QtInProcessKernelManager()

            # 启动内核
            self.kernel_manager.start_kernel(show_banner=True)

            # 设置 GUI 后端
            self.kernel_manager.kernel.gui = "qt"

            # 通知主线程内核已就绪
            self.kernel_ready.emit(self.kernel_manager)

        except Exception as e:
            self.error_occurred.emit(
                f"错误：内核初始化失败 - {e}\n请确保已安装：pip install ipython qtconsole"
            )


class IPythonConsoleTab(QWidget):
    """IPython 控制台前端界面 - 使用 RichJupyterWidget"""

    ipython_status_change = Signal(str)
    agent_context_length_change = Signal(int)

    def __init__(self):
        super().__init__()
        self.kernel_manager = None
        self.kernel_client = None
        self.console_widget = None
        self.kernel_thread = None
        self.variables_table = None
        self.is_generating = False  # 标记是否正在生成
        self.token_count = -1  # 当前上下文 token 数量

        # 先初始化 UI（不阻塞）
        self.init_ui()
        # 在后台线程中初始化内核
        self.init_kernel_async()

        # 安装事件过滤器以捕获 Ctrl+C
        self.installEventFilter(self)

    def init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # ========== 顶部工具条 ==========
        self.toolbar_widget = self._create_toolbar()
        main_layout.addWidget(self.toolbar_widget)

        # 创建分割器（左右布局）
        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)

        # 左侧：IPython 控制台
        console_group = QGroupBox("IPython Console")
        console_layout = QVBoxLayout()
        console_group.setLayout(console_layout)

        self.console_widget = RichJupyterWidget(parent=self)
        # 设置字体和背景色（通过样式表）
        # 注意：背景色由主题管理器统一控制，这里只设置字体
        self.console_widget.setStyleSheet("font-family: Consolas; font-size: 10pt;")
        self.console_widget.setObjectName("consoleWidget")
        console_layout.addWidget(self.console_widget)

        # 右侧：变量表格
        variables_group = QGroupBox("Variables")
        variables_layout = QVBoxLayout()
        variables_group.setLayout(variables_layout)

        # 创建变量表格（稍后会在 init_kernel 中传入 kernel_manager）
        self.variables_table = VariablesTable()
        variables_layout.addWidget(self.variables_table)

        # 添加到分割器
        splitter.addWidget(console_group)
        splitter.addWidget(variables_group)

        # 设置初始比例（左侧 70%，右侧 30%）
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)

        self.register_system_methods()

    def _create_toolbar(self) -> QWidget:
        """创建顶部工具条"""
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout()
        toolbar_widget.setLayout(toolbar_layout)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)

        # 设置工具条样式和固定高度
        toolbar_widget.setStyleSheet("")
        # 设置固定高度（40px），不随窗口拉伸
        toolbar_widget.setMaximumHeight(40)
        toolbar_widget.setMinimumHeight(40)

        # 清空按钮
        self.clear_btn = QPushButton("🗑️ 清空")
        self.clear_btn.setObjectName("dangerBtn")
        self.clear_btn.clicked.connect(self.clear_console)
        # 按钮固定高度
        self.clear_btn.setMaximumHeight(30)
        self.clear_btn.setMinimumHeight(30)
        toolbar_layout.addWidget(self.clear_btn)

        # 重启按钮
        self.restart_btn = QPushButton("🔄 重启")
        self.restart_btn.setObjectName("primaryBtn")
        self.restart_btn.clicked.connect(self.restart_console)
        # 按钮固定高度
        self.restart_btn.setMaximumHeight(30)
        self.restart_btn.setMinimumHeight(30)
        toolbar_layout.addWidget(self.restart_btn)

        toolbar_layout.addSpacing(20)

        # MCP 工具管理按钮
        self.mcp_tools_btn = QPushButton("🔧 MCP 工具")
        self.mcp_tools_btn.setObjectName("warningBtn")
        self.mcp_tools_btn.clicked.connect(self.show_mcp_tools_manager)
        # 按钮固定高度
        self.mcp_tools_btn.setMaximumHeight(30)
        self.mcp_tools_btn.setMinimumHeight(30)
        toolbar_layout.addWidget(self.mcp_tools_btn)

        toolbar_layout.addSpacing(20)

        # Agent 状态显示控件
        status_widget = QWidget()
        status_layout = QHBoxLayout()
        status_widget.setLayout(status_layout)
        status_layout.setContentsMargins(0, 0, 0, 0)
        # 状态控件也设置固定高度
        status_widget.setMaximumHeight(32)
        status_widget.setMinimumHeight(32)

        # 状态标签
        self.status_label = QLabel("⚪ 空闲")
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 4px 12px;
                border-radius: 4px;
                background-color: #e0e0e0;
                color: #666;
                font-weight: bold;
            }
        """)
        # 标签固定高度
        self.status_label.setMaximumHeight(30)
        self.status_label.setMinimumHeight(30)
        status_layout.addWidget(self.status_label)

        # 停止生成按钮（默认隐藏）
        self.stop_btn = QPushButton("⏹️ 停止生成")
        self.stop_btn.setObjectName("warningBtn")
        self.stop_btn.clicked.connect(self.stop_generation)
        # 按钮固定高度
        self.stop_btn.setMaximumHeight(30)
        self.stop_btn.setMinimumHeight(30)
        self.stop_btn.setVisible(False)  # 初始隐藏
        status_layout.addWidget(self.stop_btn)

        # Token 数量显示
        self.token_label = QLabel("📊 Tokens: -1")
        self.token_label.setStyleSheet("""
            QLabel {
                padding: 4px 12px;
                border-radius: 4px;
                background-color: #fff;
                color: #333;
                font-weight: bold;
                border: 1px solid #ddd;
            }
        """)
        # 标签固定高度
        self.token_label.setMaximumHeight(30)
        self.token_label.setMinimumHeight(30)
        status_layout.addWidget(self.token_label)
        self.agent_context_length_change.connect(self.update_token_display)

        toolbar_layout.addStretch()
        toolbar_layout.addWidget(status_widget)
        self.ipython_status_change.connect(self.update_status_display)
        self.ipython_status_change.emit("idle")
        return toolbar_widget

    def show_mcp_tools_manager(self):
        """显示 MCP 工具管理器对话框"""
        # 创建 MCP 工具管理器实例，并传入 agent 引用
        dialog = MCPToolsManagerWidget(parent=self, agent_instance=self.agent_instance)

        # 连接信号到处理方法
        dialog.tools_selection_changed.connect(self._on_mcp_tools_selection_changed)

        dialog.exec_()

    def _on_mcp_tools_selection_changed(
        self, enabled_tools: list, disabled_tools: list
    ):
        """
        处理 MCP 工具选择变化

        Args:
            enabled_tools: 启用的工具名称列表
            disabled_tools: 禁用的工具名称列表
        """
        # 更新 Agent 的过滤条件
        if hasattr(self, "agent_instance") and self.agent_instance:
            self.agent_instance.update_mcp_tools_filter(enabled_tools, disabled_tools)

    def clear_console(self):
        """清空控制台内容"""
        if self.console_widget:
            self.console_widget.reset(clear=True)
            print("[IPythonConsoleTab] 控制台已清空")

    def restart_console(self):
        """重启控制台（重新初始化内核）"""
        print("[IPythonConsoleTab] 正在重启控制台...")

        # 先停止当前的内核
        if self.kernel_client:
            self.kernel_client.stop_channels()
        if self.kernel_manager:
            self.kernel_manager.shutdown_kernel()

        # 重置状态
        self.kernel_manager = None
        self.kernel_client = None

        # 清空控制台
        if self.console_widget:
            self.console_widget.reset()
            self.console_widget._append_plain_text("正在重新启动 IPython 内核...\n")

        # 重新初始化内核
        self.init_kernel_async()
        print("[IPythonConsoleTab] 控制台重启完成")

    def stop_generation(self):
        """停止当前正在进行的生成"""
        if hasattr(self, "agent_instance") and self.agent_instance:
            if hasattr(self.agent_instance, "output_handler"):
                self.agent_instance.output_handler.stop()
                self.is_generating = False
                self.update_status_display()
                print("[IPythonConsoleTab] 已停止生成")
        else:
            print("[IPythonConsoleTab] 警告：没有找到正在运行的生成任务")

    def update_token_display(self, tokens: int | None = None):
        """更新 token 显示"""
        # logger.info("[IPythonConsoleTab] 更新 token 显示: %s", tokens)
        if tokens is not None:
            self.token_label.setText(f"📊 Tokens: {tokens}")

    def update_status_display(self, status: str = "idle", tokens: int | None = None):
        """
        更新状态显示

        Args:
            status: 状态字符串 ("idle", "generating", "finished", "error")
            tokens: token 数量（可选）
        """
        from PySide6.QtCore import QTimer
        from .plugin_manager import exec_main_thread_callback

        def update():
            # 更新状态标签
            if status == "idle":
                self.status_label.setText("⚪ 空闲")
                self.status_label.setStyleSheet("""
                    QLabel {
                        padding: 6px 12px;
                        border-radius: 4px;
                        background-color: #e0e0e0;
                        color: #666;
                        font-weight: bold;
                    }
                """)
                self.stop_btn.setVisible(False)
            elif status == "generating":
                self.status_label.setText("🟢 运行中")
                self.status_label.setStyleSheet("""
                    QLabel {
                        padding: 6px 12px;
                        border-radius: 4px;
                        background-color: #4CAF50;
                        color: white;
                        font-weight: bold;
                    }
                """)
                self.stop_btn.setVisible(True)
            elif status == "finished":
                self.status_label.setText("✅ 生成完毕")
                self.status_label.setStyleSheet("""
                    QLabel {
                        padding: 6px 12px;
                        border-radius: 4px;
                        background-color: #2196F3;
                        color: white;
                        font-weight: bold;
                    }
                """)
                self.stop_btn.setVisible(False)
            elif status == "error":
                self.status_label.setText("🔴 错误")
                self.status_label.setStyleSheet("""
                    QLabel {
                        padding: 6px 12px;
                        border-radius: 4px;
                        background-color: #f44336;
                        color: white;
                        font-weight: bold;
                    }
                """)
                self.stop_btn.setVisible(False)

            # 更新 token 数量
            if tokens is not None:
                self.token_count = tokens
                self.token_label.setText(f"📊 Tokens: {tokens}")

        # 在主线程中执行
        exec_main_thread_callback(update)

    def eventFilter(self, obj, event):
        """
        事件过滤器 - 捕获 Ctrl+C 快捷键

        Args:
            obj: 事件对象
            event: 事件实例

        Returns:
            bool: 是否处理了该事件
        """
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QKeyEvent

        if event.type() == QEvent.Type.KeyPress:
            # 检查是否是 Ctrl+C 组合键
            key_event = event
            if isinstance(key_event, QKeyEvent):
                if key_event.key() in (Qt.Key.Key_C,) and (
                    key_event.modifiers() & Qt.KeyboardModifier.ControlModifier
                ):
                    print("[IPythonConsoleTab] 检测到 Ctrl+C，正在停止生成...")
                    self.stop_generation()
                    return True  # 阻止事件继续传递

        # 其他事件交给基类处理
        return super().eventFilter(obj, event)

    def register_system_methods(self):
        """注册系统方法，可以获得 ipython 中的变量"""
        pm = get_plugin_manager()
        pm._register_system_method(
            "set_variable", self.set_variable, {"enable_mcp": True}
        )
        pm._register_system_method(
            "get_variable", self.get_variable, {"enable_mcp": True}
        )
        pm._register_system_method(
            "execute_code", self.execute_code, {"enable_mcp": True}
        )
        pm._register_system_method(
            "clear_console", self.clear_console, {"enable_mcp": False}
        )
        pm._register_system_method(
            "restart_console", self.restart_console, {"enable_mcp": False}
        )
        pm._register_system_method(
            "get_mcp_tools_status", self.get_mcp_tools_status, {"enable_mcp": True}
        )

    def execute_code(self, code: str):
        """
        在IPython内核中执行代码

        Args:
            code: (str) 要执行的代码，可以是语句或者代码块。注意如果只是赋值，请使用专门的设置变量的工具

        Returns:
            dict: {"success": bool, "output": str, "result": object, "error": str}
            success: 是否执行成功，output: print输出的内容，result: IPython代码块执行的返回值，error: 错误信息
        """
        from PySide6.QtCore import QTimer
        from .plugin_manager import exec_main_thread_callback

        if self.kernel_manager:
            print("\n\n")
            display(Markdown(f"## 开始执行代码块：\n```python\n{code}```"))
            print("\n\n")
            with capture_output() as captured:
                result = self.kernel_manager.kernel.shell.run_cell(
                    code, store_history=False, silent=True
                )
                if self.variables_table:
                    exec_main_thread_callback(
                        lambda: QTimer.singleShot(
                            0, self.variables_table.refresh_variables
                        )
                    )
            return {
                "success": True,
                "output": captured.stdout,
                "result": result.result,
                "error": (
                    result.error_in_exec if result.error_in_exec else captured.stderr
                ),
            }
        else:
            print("[IPythonConsoleTab] 警告：kernel_manager 未就绪，无法执行代码")
            return {
                "success": False,
                "output": "",
                "result": "",
                "error": "警告：kernel_manager 未就绪，无法执行代码",
            }

    def get_variable(self, name: str):
        """
        获取IPython内核中的变量
        Args:
            name (str): 变量名

        Returns:
            object: 变量值，任意类型的值均可
        """
        if self.kernel_manager:
            return self.kernel_manager.kernel.shell.user_ns.get(name)
        return None

    def set_variable(self, name: str, value: object):
        """
        为IPython内核设置变量，可以用于记忆一些数据

        Args:
            name (str): 变量名
            value (object): 变量值，任意类型的值均可

        Returns:
            bool: 设置是否成功
        """
        from PySide6.QtCore import QTimer
        from .plugin_manager import exec_main_thread_callback

        if self.kernel_manager:
            self.kernel_manager.kernel.shell.push({name: value})
            if self.variables_table:
                exec_main_thread_callback(
                    lambda: QTimer.singleShot(0, self.variables_table.refresh_variables)
                )
            return True
        else:
            return False

    def get_mcp_tools_status(self) -> dict:
        """
        获取 MCP 工具的启用状态

        Returns:
            dict: {"enabled": list, "disabled": list, "total": int}
            - enabled: 启用的工具名称列表
            - disabled: 禁用的工具名称列表
            - total: 总工具数量
        """
        if hasattr(self, "agent_instance") and self.agent_instance:
            agent = self.agent_instance
            return {
                "enabled": list(agent.mcp_tools_enabled),
                "disabled": list(agent.mcp_tools_disabled),
                "total": len(agent.mcp_tools_enabled) + len(agent.mcp_tools_disabled),
            }
        else:
            # 如果没有 agent，返回所有 MCP 工具都为启用状态
            from app_qt.plugin_manager import get_plugin_manager

            pm = get_plugin_manager()
            all_methods = pm.get_all_methods(include_extra_data=True)
            mcp_tools = [
                m["name"]
                for m in all_methods
                if m.get("extra_data", {}).get("enable_mcp", False)
            ]
            return {"enabled": mcp_tools, "disabled": [], "total": len(mcp_tools)}

    def init_kernel_async(self):
        """在后台线程中异步初始化内核"""
        # 显示加载提示
        if self.console_widget:
            self.console_widget._append_plain_text("正在启动 IPython 内核...\n")

        # 创建并启动内核初始化线程
        self.kernel_thread = KernelInitThread()
        self.kernel_thread.kernel_ready.connect(self._on_kernel_ready)
        self.kernel_thread.error_occurred.connect(self._on_kernel_error)
        self.kernel_thread.start()

    def _on_kernel_ready(self, kernel_manager):
        """内核就绪后的回调（在主线程中执行）"""
        self.kernel_manager = kernel_manager

        # 获取内核客户端
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()

        # 将内核连接到控制台
        if self.console_widget:
            self.console_widget.kernel_manager = self.kernel_manager
            self.console_widget.kernel_client = self.kernel_client
            logger.info("[IPythonConsoleTab] 内核已启动并连接到控制台")
        logger.info(f"[IPythonConsoleTab] 变量表格: {self.variables_table}")
        # 将内核连接到变量表格
        if self.variables_table:
            self.variables_table.kernel_manager = self.kernel_manager
            self.variables_table.refresh_variables()  # 初始化时刷新一次
            logger.info(
                f"[IPythonConsoleTab] 变量表格已初始化, {self.variables_table.get_variables()}"
            )
            # 绑定执行后的回调 - 监听 kernel.shell.events 的 post_execute
            shell = self.kernel_manager.kernel.shell
            # 注册 post_execute 事件处理器，在每次执行后刷新变量表格
            shell.events.register("post_execute", self._on_command_executed)

        # ========== 注入 IPython 插件 API ==========
        self._inject_plugins_api()

        # ========== 注入 IPython LLM Agent API ==========
        self._inject_llm_agent_api()

        if self.console_widget:
            self.console_widget._append_plain_text("IPython 内核已就绪！\n\n")

    def _on_kernel_error(self, error_msg):
        """内核初始化错误处理（在主线程中执行）"""
        if self.console_widget:
            self.console_widget._append_plain_text(error_msg)

    def _inject_plugins_api(self):
        """向 IPython 命名空间注入插件 API（在主线程中执行）"""
        try:
            from app_qt.ipython_plugins_bridge import init_ipython_plugins_api
            from app_qt.plugin_manager import get_plugin_manager

            # 获取插件管理器实例
            plugin_manager = get_plugin_manager()

            # 创建插件 API 对象
            plugins_api = init_ipython_plugins_api(plugin_manager)

            # 获取 IPython shell 的命名空间
            # kernel_manager 已经在 _on_kernel_ready 中设置好了
            if self.kernel_manager and hasattr(self.kernel_manager, "kernel"):
                shell = self.kernel_manager.kernel.shell

                # 将 plugins 对象注入到用户命名空间
                shell.user_ns["plugins"] = plugins_api

                print("[IPythonConsoleTab] 已注入 plugins API 到 IPython 命名空间")
            else:
                print(
                    "[IPythonConsoleTab] 警告：kernel_manager 未就绪，无法注入插件 API"
                )

        except Exception as e:
            print(f"[IPythonConsoleTab] 注入插件 API 失败：{e}")
            import traceback

            traceback.print_exc()

    def _inject_llm_agent_api(self):
        """向 IPython 命名空间注入 LLM Agent API（在主线程中执行）"""
        try:
            from app_qt.ipython_llm_bridge import init_ipython_llm_agent_api
            from app_qt.plugin_manager import get_plugin_manager

            # 获取插件管理器实例
            plugin_manager = get_plugin_manager()

            # 初始化 LLM Agent API
            agent = init_ipython_llm_agent_api(
                ipython_tab=self, plugin_manager=plugin_manager
            )

            # 保存 agent 实例引用，用于控制停止等操作
            self.agent_instance = agent

            # 绑定 agent 的状态变化信号
            if hasattr(agent, "output_handler"):
                agent.output_handler.chunk_text_updated.connect(
                    self._on_agent_text_update
                )
                agent.output_handler.stream_finish.connect(self._on_agent_stream_finish)
                agent.output_handler.error_occurred.connect(self._on_agent_error)

            print("[IPythonConsoleTab] 已注入 agent API 到 IPython 命名空间")

        except Exception as e:
            print(f"[IPythonConsoleTab] 注入 LLM Agent API 失败：{e}")
            import traceback

            traceback.print_exc()

    def _on_command_executed(self, result=None):
        """命令执行后的回调函数"""
        if hasattr(self, "variables_table") and self.variables_table:
            # 延迟一小段时间刷新，确保内核状态已更新
            from PySide6.QtCore import QTimer
            from .plugin_manager import exec_main_thread_callback

            exec_main_thread_callback(
                lambda: QTimer.singleShot(100, self.variables_table.refresh_variables)
            )
            # QTimer.singleShot(100, self.variables_table.refresh_variables)

    def _on_agent_text_update(self, text: str):
        """Agent 文本更新回调 - 更新状态为生成中"""
        if not self.is_generating:
            self.is_generating = True
            self.update_status_display(status="generating")

    def _on_agent_stream_finish(self, next_action: str):
        """Agent 流式输出完成回调"""
        self.is_generating = False
        # 如果是 CALL_TOOL，保持生成状态；否则标记为完成
        if next_action == "FINISH":
            self.update_status_display(status="finished")
        else:
            # CALL_TOOL 等情况，继续保持生成状态
            self.update_status_display(status="generating")

    def _on_agent_error(self, error_msg: str):
        """Agent 错误处理回调"""
        self.is_generating = False
        self.update_status_display(status="error")

    def closeEvent(self, event):
        """清理资源"""
        # 先停止内核线程
        if self.kernel_thread and self.kernel_thread.isRunning():
            self.kernel_thread.quit()
            self.kernel_thread.wait()

        # 然后停止内核客户端和管理器
        if self.kernel_client:
            self.kernel_client.stop_channels()
        if self.kernel_manager:
            self.kernel_manager.shutdown_kernel()
        event.accept()
