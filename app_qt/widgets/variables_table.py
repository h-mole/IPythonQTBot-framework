"""
变量表格组件 - 显示 IPython 内核中的当前变量
需要安装：pip install pandas
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QHeaderView,
)
from PySide6.QtGui import QFont
from app_qt.plugin_manager import get_plugin_manager
from qtconsole.inprocess import QtInProcessKernelManager


class VariablesTable(QWidget):
    """变量表格组件 - 显示 IPython 内核中的变量"""

    def __init__(self, kernel_manager=None):
        super().__init__()
        self.kernel_manager = kernel_manager
        self.variables_data = []

        self.init_ui()
        self.refresh_variables()
        self.register_system_methods()

    def register_system_methods(self):
        """
        注册系统方法，可以获得ipython中的变量
        """
        pm = get_plugin_manager()
        pm._register_system_method(
            "get_variables", self.get_variables, {"enable_mcp": True}
        )

    def init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # 标题和刷新按钮
        header_layout = QHBoxLayout()

        title_label = QLabel("📊 变量监视器")
        title_label.setFont(QFont("Microsoft YaHei UI", 12, 75))
        title_label.setStyleSheet("padding: 5px;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh_variables)
        refresh_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                border-radius: 3px;
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        header_layout.addWidget(refresh_btn)

        main_layout.addLayout(header_layout)

        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["变量名", "类型", "值", "大小"])

        # 设置表格属性
        header = self.table.horizontalHeader()
        # 使用整数值 1 代表 QHeaderView.Stretch (避免类型检查错误)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode(1))  # 第 1 列拉伸
        header.setSectionResizeMode(1, QHeaderView.ResizeMode(1))  # 第 2 列拉伸
        header.setSectionResizeMode(2, QHeaderView.ResizeMode(1))  # 第 3 列拉伸
        header.setSectionResizeMode(3, QHeaderView.ResizeMode(1))  # 第 4 列拉伸
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ddd;
                font-family: Consolas;
                font-size: 10pt;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: none;
                font-weight: bold;
            }
        """)

        main_layout.addWidget(self.table)

    def get_variables(self):
        """
        获取 IPython 内核中的变量
        
        Args: 
            无
        Returns:
            dict: 变量字典，包含变量名、类型、值和大小信息。比如：{"var1": {"type": "int", "value": "1", "size": "1"}, ...}
        """
        try:
            # 使用 shell 的用户命名空间直接获取变量信息
            shell = self.kernel_manager.kernel.shell
            user_ns = shell.user_ns

            # 获取用户定义的全局变量（排除内置和下划线开头的）
            import sys
            import types

            # 需要排除的保留变量名
            reserved_names = {
                "In",
                "Out",
                "exit",
                "quit",
                "get_ipython",
                "open",
                "input",
                "help",
                "_",
                "__",
                "___",
            }

            user_vars = {}
            for name, value in user_ns.items():
                # 排除以下变量：
                # 1. 下划线开头的
                # 2. 系统模块
                # 3. 保留变量名
                # 4. 可调用对象（函数、类、方法等）
                if (
                    not name.startswith("_")
                    and name not in sys.modules
                    and name not in reserved_names
                    and not callable(value)
                    and not isinstance(
                        value, (types.FunctionType, types.MethodType, type)
                    )
                ):
                    try:
                        var_type = type(value).__name__
                        var_str = str(value)[:100]  # 限制长度
                        var_size = len(str(value)) if hasattr(value, "__len__") else "-"
                        user_vars[name] = {
                            "type": var_type,
                            "value": var_str,
                            "size": var_size,
                        }
                    except Exception as e:
                        user_vars[name] = {
                            "type": type(value).__name__,
                            "value": "<无法显示>",
                            "size": "-",
                        }

            return user_vars

        except Exception as e:
            print(f"刷新变量失败：{e}")
            return {}

    def refresh_variables(self):
        """从 IPython 内核获取并刷新变量列表"""
        if not self.kernel_manager:
            return

        try:
            user_vars = self.get_variables()
            # 更新表格
            self.update_table(user_vars)

        except Exception as e:
            print(f"刷新变量失败：{e}")

    def update_table(self, variables_dict):
        """更新表格数据"""
        if not variables_dict:
            self.table.setRowCount(0)
            return

        self.table.setRowCount(len(variables_dict))

        for row, (var_name, var_info) in enumerate(variables_dict.items()):
            # 变量名
            name_item = QTableWidgetItem(var_name)
            name_item.setForeground(self.table.palette().text())
            self.table.setItem(row, 0, name_item)

            # 类型
            type_item = QTableWidgetItem(var_info.get("type", "Unknown"))
            type_item.setForeground(self.table.palette().text())
            self.table.setItem(row, 1, type_item)

            # 值
            value_item = QTableWidgetItem(var_info.get("value", ""))
            value_item.setForeground(self.table.palette().text())
            self.table.setItem(row, 2, value_item)

            # 大小
            size_item = QTableWidgetItem(str(var_info.get("size", "-")))
            size_item.setForeground(self.table.palette().text())
            self.table.setItem(row, 3, size_item)
