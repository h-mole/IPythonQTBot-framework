"""
IPython 控制台标签页 - PySide6 版本
使用 qtconsole.rich_jupyter_widget.RichJupyterWidget
需要安装：pip install ipython qtconsole
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QSplitter
from PySide6.QtGui import QFont, Qt
from PySide6.QtCore import QThread, Signal
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager
import sys
from app_qt.plugin_manager import get_plugin_manager
from IPython.utils.capture import capture_output
# 导入变量表格组件
from .widgets.variables_table import VariablesTable


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

    def __init__(self):
        super().__init__()
        self.kernel_manager = None
        self.kernel_client = None
        self.console_widget = None
        self.kernel_thread = None

        # 先初始化 UI（不阻塞）
        self.init_ui()
        # 在后台线程中初始化内核
        self.init_kernel_async()

    def init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # 创建分割器（左右布局）
        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)

        # 左侧：IPython 控制台
        console_group = QGroupBox("IPython Console")
        console_layout = QVBoxLayout()
        console_group.setLayout(console_layout)

        self.console_widget = RichJupyterWidget(parent=self)
        # 设置字体（通过样式表）
        self.console_widget.setStyleSheet("font-family: Consolas; font-size: 10pt;")
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

    def register_system_methods(self):
        """注册系统方法，可以获得ipython中的变量"""
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
        if self.kernel_manager:
            with capture_output() as captured:
                result = self.kernel_manager.kernel.shell.run_cell(code, store_history=True, silent=True)
                if self.variables_table:
                    # 获取当前线程对象
                    current_qthread = QThread.currentThread()

                    # 打印线程信息
                    print(f"当前QThread对象: {current_qthread}")
                    print(f"线程对象名称: {current_qthread.objectName()}")
                    print(f"线程ID: {QThread.currentThreadId()}")
                    QTimer.singleShot(0, self.variables_table.refresh_variables)
            return {
                "success": True,
                "output": captured.stdout,
                "result": result.result,
                "error": result.error_in_exec if result.error_in_exec else captured.stderr
            }
        else:
            print("[IPythonConsoleTab] 警告：kernel_manager 未就绪，无法执行代码")
            return {"success": False, "output": "", "result": "", "error": "警告：kernel_manager 未就绪，无法执行代码"}

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
        if self.kernel_manager:
            self.kernel_manager.kernel.shell.push({name: value})
            if self.variables_table:
                QTimer.singleShot(0, self.variables_table.refresh_variables)
            return True
        else:
            return False

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

        # 将内核连接到变量表格
        if hasattr(self, "variables_table") and self.variables_table:
            self.variables_table.kernel_manager = self.kernel_manager
            self.variables_table.refresh_variables()  # 初始化时刷新一次

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
            agent = init_ipython_llm_agent_api(plugin_manager=plugin_manager)

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

            QTimer.singleShot(100, self.variables_table.refresh_variables)

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
