"""
每日任务提醒器插件 - 提供任务管理和提醒功能
"""

import os
import sys
import json
from datetime import datetime, time as dt_time
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QPushButton,
    QLabel,
    QFrame,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QDialog,
    QLineEdit,
    QTextEdit,
    QDateTimeEdit,
    QFormLayout,
    QDialogButtonBox,
    QCheckBox,
    QTimeEdit,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QMenu,
)
from PySide6.QtCore import Qt, QTimer, QTime, Signal
from PySide6.QtGui import QFont, QAction, QColor
from PySide6.QtCore import QDateTime as QtCore_QDateTime
import openpyxl
from openpyxl.utils import get_column_letter
import plyer
from app_qt.configs import PLUGIN_DATA_DIR
# 默认分类
DEFAULT_CATEGORIES = ["论文", "项目"]
DEFAULT_SUBCATEGORIES = ["行政", "项目", "会议", "学习"]
DEFAULT_STATUSES = ["未完成", "已完成", "进行中", "已取消"]
REMINDER_TYPES = ["每天", "当天", "仅一次"]

# 插件数据文件路径
DAILY_TASKS_DATA_DIR = os.path.join(PLUGIN_DATA_DIR, "daily_tasks")

TASKS_FILE = os.path.join(DAILY_TASKS_DATA_DIR, "daily_tasks.xlsx")
CATEGORIES_FILE = os.path.join(DAILY_TASKS_DATA_DIR, "task_categories.json")


class MultiSelectFilter(QWidget):
    """多选筛选器组件"""

    filterChanged = Signal()

    def __init__(self, label_text, items=None, parent=None):
        super().__init__(parent)
        self.items = items or []
        self.all_option = "全部"

        # 创建布局
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.setLayout(layout)

        # 标签
        layout.addWidget(QLabel(label_text))

        # 筛选按钮
        self.filter_btn = QPushButton("请选择...")
        self.filter_btn.setMinimumWidth(120)
        self.filter_btn.clicked.connect(self.show_menu)
        layout.addWidget(self.filter_btn)

        # 选中状态记录
        self.selected_items = set()
        self.select_all = True  # 默认全选

        # 更新按钮文本
        self.update_button_text()

    def show_menu(self):
        """显示选择菜单"""
        menu = QMenu(self)

        # "全部"选项
        all_action = menu.addAction(self.all_option)
        all_action.setCheckable(True)
        all_action.setChecked(self.select_all)
        all_action.triggered.connect(lambda: self.toggle_all())
        menu.addSeparator()

        # 其他选项
        self.item_actions = {}
        for item in self.items:
            action = menu.addAction(item)
            action.setCheckable(True)
            # 如果是全选模式，所有项都勾选
            is_selected = self.select_all or item in self.selected_items
            action.setChecked(is_selected)
            self.item_actions[item] = action
            action.triggered.connect(lambda checked, name=item: self.toggle_item(name))

        # 显示菜单
        menu.exec_(self.filter_btn.mapToGlobal(self.filter_btn.rect().bottomLeft()))

    def toggle_all(self):
        """切换全选状态"""
        self.select_all = not self.select_all
        if self.select_all:
            self.selected_items.clear()
        self.update_button_text()
        self.filterChanged.emit()

    def toggle_item(self, item_name):
        """切换单项选择状态"""
        if self.select_all:
            # 如果当前是全选，取消某个项
            self.select_all = False
            # 初始化选中集合为除了当前点击项之外的所有项
            self.selected_items = set(self.items) - {item_name}
        else:
            # 如果当前不是全选，切换该项
            if item_name in self.selected_items:
                self.selected_items.remove(item_name)
            else:
                self.selected_items.add(item_name)

            # 检查是否变成了全选
            if len(self.selected_items) == len(self.items):
                self.select_all = True
                self.selected_items.clear()

        self.update_button_text()
        self.filterChanged.emit()

    def update_button_text(self):
        """更新按钮显示文本"""
        if self.select_all:
            self.filter_btn.setText(f"全部 ({len(self.items)})")
        elif len(self.selected_items) == 0:
            self.filter_btn.setText("未选择任何项")
        elif len(self.selected_items) <= 3:
            self.filter_btn.setText(", ".join(sorted(self.selected_items)))
        else:
            self.filter_btn.setText(f"已选 {len(self.selected_items)} 项")

    def get_selected(self):
        """获取选中的项目"""
        if self.select_all:
            return set(self.items)
        return self.selected_items.copy()

    def is_select_all(self):
        """是否全选"""
        return self.select_all

    def set_items(self, items):
        """设置筛选项"""
        self.items = items
        if self.select_all:
            self.selected_items.clear()
        self.update_button_text()


class TaskDialog(QDialog):
    """任务编辑对话框"""

    def __init__(self, parent=None, task_data=None):
        super().__init__(parent)
        self.task_data = task_data

        # 加载用户自定义分类
        self.load_user_categories()

        self.init_ui()

    def load_user_categories(self):
        """加载用户自定义的分类"""
        try:
            if os.path.exists(CATEGORIES_FILE):
                with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.user_categories = data.get("categories", DEFAULT_CATEGORIES)
                    self.user_subcategories = data.get(
                        "subcategories", DEFAULT_SUBCATEGORIES
                    )
            else:
                self.user_categories = DEFAULT_CATEGORIES
                self.user_subcategories = DEFAULT_SUBCATEGORIES
        except Exception as e:
            print(f"Error loading categories: {e}")
            self.user_categories = DEFAULT_CATEGORIES
            self.user_subcategories = DEFAULT_SUBCATEGORIES

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("添加/编辑任务")
        self.setMinimumWidth(500)

        layout = QFormLayout()
        self.setLayout(layout)

        # 任务大类
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(self.user_categories)
        if self.task_data and self.task_data.get("category"):
            self.category_combo.setCurrentText(self.task_data["category"])
        layout.addRow("任务大类:", self.category_combo)

        # 任务小类
        self.subcategory_combo = QComboBox()
        self.subcategory_combo.setEditable(True)
        self.subcategory_combo.addItems(self.user_subcategories)
        if self.task_data and self.task_data.get("subcategory"):
            self.subcategory_combo.setCurrentText(self.task_data["subcategory"])
        layout.addRow("任务小类:", self.subcategory_combo)

        # 任务说明
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        if self.task_data and self.task_data.get("description"):
            self.description_edit.setPlainText(self.task_data["description"])
        layout.addRow("任务说明:", self.description_edit)

        # 完成日期
        self.due_date_edit = QDateTimeEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDisplayFormat("yyyy-MM-dd")
        if self.task_data and self.task_data.get("due_date"):
            try:
                due_date = datetime.strptime(self.task_data["due_date"], "%Y-%m-%d")
                qt_datetime = QtCore_QDateTime(
                    due_date.year, due_date.month, due_date.day, 0, 0, 0  # 时间设置为 0
                )
                self.due_date_edit.setDateTime(qt_datetime)
            except:
                self.due_date_edit.setDateTime(QtCore_QDateTime.currentDateTime())
        else:
            self.due_date_edit.setDateTime(QtCore_QDateTime.currentDateTime())
        layout.addRow("任务完成日期:", self.due_date_edit)

        # 提醒方式
        self.reminder_type_combo = QComboBox()
        self.reminder_type_combo.addItems(REMINDER_TYPES)
        if self.task_data and self.task_data.get("reminder_type"):
            self.reminder_type_combo.setCurrentText(self.task_data["reminder_type"])
        layout.addRow("提醒方式:", self.reminder_type_combo)

        # 提醒时间（只设置时刻，不设置日期）
        self.reminder_time_edit = QTimeEdit()
        self.reminder_time_edit.setDisplayFormat("HH:mm")

        # 特殊时间下拉菜单
        self.special_time_combo = QComboBox()
        self.special_time_combo.addItem("一般日期", "normal")
        self.special_time_combo.addItem("无固定期限", "no_deadline")
        self.special_time_combo.addItem("长期", "long_term")
        self.special_time_combo.currentTextChanged.connect(self.on_special_time_changed)

        # 创建水平布局放置时间选择器和下拉菜单
        time_layout = QHBoxLayout()
        time_layout.setSpacing(5)
        time_layout.addWidget(self.reminder_time_edit)
        time_layout.addWidget(self.special_time_combo)

        if self.task_data and self.task_data.get("reminder_time"):
            try:
                # 尝试从旧格式解析（包含日期）
                reminder_time = datetime.strptime(
                    self.task_data["reminder_time"], "%Y-%m-%d %H:%M"
                )
                time_obj = QTime(reminder_time.hour, reminder_time.minute)
                self.reminder_time_edit.setTime(time_obj)
                # 检查是否是特殊日期
                if "1999-09-09" in self.task_data.get("due_date", ""):
                    self.special_time_combo.setCurrentIndex(1)  # 无固定期限
                    self.reminder_time_edit.setEnabled(False)
                elif "1999-09-10" in self.task_data.get("due_date", ""):
                    self.special_time_combo.setCurrentIndex(2)  # 长期
                    self.reminder_time_edit.setEnabled(False)
            except:
                try:
                    # 尝试从新格式解析（只有时间）
                    reminder_time = datetime.strptime(
                        self.task_data["reminder_time"], "%H:%M"
                    )
                    time_obj = QTime(reminder_time.hour, reminder_time.minute)
                    self.reminder_time_edit.setTime(time_obj)
                except:
                    self.reminder_time_edit.setTime(QTime.fromString("10:30", "HH:mm"))
        else:
            self.reminder_time_edit.setTime(QTime.currentTime())

        layout.addRow("提醒时间:", time_layout)

        # 完成状态
        self.status_combo = QComboBox()
        self.status_combo.addItems(["未完成", "已完成", "进行中", "已取消"])
        if self.task_data and self.task_data.get("status"):
            self.status_combo.setCurrentText(self.task_data["status"])
        layout.addRow("完成状态:", self.status_combo)

        # 备注
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        if self.task_data and self.task_data.get("notes"):
            self.notes_edit.setPlainText(self.task_data["notes"])
        layout.addRow("备注:", self.notes_edit)

        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def on_special_time_changed(self, text):
        """特殊时间选项改变时的处理"""
        current_data = self.special_time_combo.currentData()
        if current_data == "normal":
            self.reminder_time_edit.setEnabled(True)
        else:
            self.reminder_time_edit.setEnabled(False)

    def get_task_data(self):
        """获取任务数据"""
        # 根据特殊时间选项设置完成日期
        special_time_type = self.special_time_combo.currentData()
        due_date = self.due_date_edit.dateTime().toString("yyyy-MM-dd")

        if special_time_type == "no_deadline":
            due_date = "1999-09-09"
        elif special_time_type == "long_term":
            due_date = "1999-09-10"

        return {
            "category": self.category_combo.currentText(),
            "subcategory": self.subcategory_combo.currentText(),
            "description": self.description_edit.toPlainText().strip(),
            "due_date": due_date,
            "reminder_type": self.reminder_type_combo.currentText(),
            "reminder_time": self.reminder_time_edit.time().toString("HH:mm"),
            "status": self.status_combo.currentText(),
            "notes": self.notes_edit.toPlainText().strip(),
        }


class TasksManagerTab(QWidget):
    """任务管理器标签页"""

    # 表格列定义
    COLUMNS = [
        "ID",
        "任务大类",
        "任务小类",
        "任务说明",
        "任务完成日期",
        "提醒方式",
        "提醒时间",
        "完成状态",
        "备注",
    ]

    def __init__(self, plugin_manager=None):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.tasks_file = TASKS_FILE
        self.categories_file = CATEGORIES_FILE
        self.tasks_data = []
        self.remind_timers = {}
        self.notified_tasks = {}  # 记录已通知的任务，避免重复通知

        # 确保数据目录存在
        os.makedirs(DAILY_TASKS_DATA_DIR, exist_ok=True)

        self.init_ui()
        self.load_tasks()

        # 启动定时器检查提醒
        self.reminder_timer = QTimer()
        self.reminder_timer.timeout.connect(self.check_reminders)
        self.reminder_timer.start(10000)  # 每 10 秒检查一次

    def init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # 顶部控制区域
        control_frame = QFrame()
        control_layout = QHBoxLayout()
        control_frame.setLayout(control_layout)

        # 筛选控件 - 使用独立的多选筛选组件
        self.category_filter = MultiSelectFilter("任务大类:", DEFAULT_CATEGORIES.copy())
        self.category_filter.filterChanged.connect(self.apply_filters)
        control_layout.addWidget(self.category_filter)

        self.subcategory_filter = MultiSelectFilter(
            "任务小类:", DEFAULT_SUBCATEGORIES.copy()
        )
        self.subcategory_filter.filterChanged.connect(self.apply_filters)
        control_layout.addWidget(self.subcategory_filter)

        self.status_filter = MultiSelectFilter("完成状态:", DEFAULT_STATUSES.copy())
        self.status_filter.filterChanged.connect(self.apply_filters)
        control_layout.addWidget(self.status_filter)

        # 加载用户自定义分类到筛选器
        self.load_categories_to_filters()

        control_layout.addStretch()

        # 排序控件
        control_layout.addWidget(QLabel("排序:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("按类别", "categories")
        self.sort_combo.addItem("按截止期限", "due")
        self.sort_combo.currentIndexChanged.connect(self.apply_filters)
        control_layout.addWidget(self.sort_combo)

        # 倒序选项
        self.reverse_check = QCheckBox("倒序")
        self.reverse_check.stateChanged.connect(self.apply_filters)
        control_layout.addWidget(self.reverse_check)

        control_layout.addStretch()

        main_layout.addWidget(control_frame)

        # 第二行：操作按钮
        button_frame = QFrame()
        button_layout = QHBoxLayout()
        button_frame.setLayout(button_layout)

        self.add_btn = QPushButton("➕ 添加任务")
        self.add_btn.clicked.connect(lambda :self.add_task(True))
        button_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("✏️ 编辑任务")
        self.edit_btn.clicked.connect(self.edit_task)
        button_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑️ 删除任务")
        self.delete_btn.clicked.connect(self.delete_task)
        button_layout.addWidget(self.delete_btn)

        self.complete_btn = QPushButton("✅ 标记完成")
        self.complete_btn.clicked.connect(self.mark_complete)
        button_layout.addWidget(self.complete_btn)

        button_layout.addStretch()

        main_layout.addWidget(button_frame)

        # 任务表格
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)

        # 设置表格属性
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setMouseTracking(True)  # 启用鼠标追踪以支持 tooltip

        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )  # 任务大类
        header.setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )  # 任务小类
        header.setSectionResizeMode(
            7, QHeaderView.ResizeMode.ResizeToContents
        )  # 完成状态
        header.setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )  # 任务完成日期
        header.setSectionResizeMode(
            5, QHeaderView.ResizeMode.ResizeToContents
        )  # 提醒方式
        header.setSectionResizeMode(
            6, QHeaderView.ResizeMode.ResizeToContents
        )  # 提醒时间
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # 任务说明
        # 设置任务说明列的宽度至少大于300
        self.table.setColumnWidth(3, 300)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)  # 备注

        # 连接双击信号到编辑函数
        self.table.cellDoubleClicked.connect(self.edit_task_on_doubleclick)

        main_layout.addWidget(self.table)

        # 底部状态栏
        status_frame = QFrame()
        status_layout = QHBoxLayout()
        status_frame.setLayout(status_layout)

        self.status_label = QLabel("总任务数：0 | 未完成：0 | 已完成：0")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self.load_tasks)
        status_layout.addWidget(self.refresh_btn)

        main_layout.addWidget(status_frame)

        self.init_default_state()

    def init_default_state(self):
        self.reverse_check.setChecked(True)
        self.sort_combo.setCurrentIndex(0)

    def load_categories_to_filters(self):
        """加载分类到筛选器"""
        try:
            if os.path.exists(self.categories_file):
                with open(self.categories_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    categories = data["categories"]
                    subcategories = data["subcategories"]
                    # 更新筛选器的项目列表
                    self.category_filter.set_items(categories)
                    self.subcategory_filter.set_items(subcategories)
                    print("Categories loaded:", categories, "Subcategories loaded:", subcategories)
            else:
                print("Categories file not found. Using default categories.", self.categories_file)
        except Exception as e:
            print(f"加载分类失败：{e}")

    def save_categories(self):
        """保存分类到文件"""
        try:
            data = {
                "categories": self.category_filter.items,
                "subcategories": self.subcategory_filter.items,
            }
            with open(self.categories_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存分类失败：{e}")

    def edit_task_on_doubleclick(self, row, column):
        """双击单元格时编辑任务"""
        self.edit_task()

    def load_tasks(self):
        """加载任务数据"""
        try:
            if os.path.exists(self.tasks_file):
                wb = openpyxl.load_workbook(self.tasks_file)
                ws = wb.active

                self.tasks_data = []
                for row_idx, row in enumerate(
                    ws.iter_rows(min_row=2, values_only=True), start=1
                ):
                    if row[0] is not None:  # ID 列不为空
                        task = {
                            "id": row[0],
                            "category": row[1] or "",
                            "subcategory": row[2] or "",
                            "description": row[3] or "",
                            "due_date": str(row[4]) if row[4] else "",
                            "reminder_type": row[5] or "",
                            "reminder_time": str(row[6]) if row[6] else "",
                            "status": row[7] or "",
                            "notes": row[8] or "",
                        }
                        # 处理旧数据中的日期时间格式，只保留日期部分
                        if task["due_date"]:
                            try:
                                # 如果是旧格式（包含时间），转换为只有日期
                                if " " in task["due_date"]:
                                    dt = datetime.strptime(
                                        task["due_date"], "%Y-%m-%d %H:%M"
                                    )
                                    task["due_date"] = dt.strftime("%Y-%m-%d")
                            except:
                                pass
                        self.tasks_data.append(task)

                wb.close()
            else:
                self.tasks_data = []
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载任务失败：{str(e)}")
            self.tasks_data = []
        # 重置已通知记录，避免重启后不再提醒
        self.notified_tasks = {}
        # print("data", self.tasks_data)
        # # self.refresh_table()
        self.update_status()
        self.apply_filters()

    def save_tasks(self):
        """保存任务数据"""
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "每日任务"

            # 写入表头
            ws.append(
                [
                    "ID",
                    "任务大类",
                    "任务小类",
                    "任务说明",
                    "任务完成日期",
                    "提醒方式",
                    "提醒时间",
                    "完成状态",
                    "备注",
                ]
            )

            # 写入数据
            for task in self.tasks_data:
                ws.append(
                    [
                        task.get("id", ""),
                        task.get("category", ""),
                        task.get("subcategory", ""),
                        task.get("description", ""),
                        task.get("due_date", ""),
                        task.get("reminder_type", ""),
                        task.get("reminder_time", ""),
                        task.get("status", ""),
                        task.get("notes", ""),
                    ]
                )

            # 自动调整列宽
            for column in ws.columns:
                max_length = 0
                column_letter = get_column_letter(column[0].column)
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width

            wb.save(self.tasks_file)
            wb.close()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存任务失败：{str(e)}")

    def refresh_table(self, filtered_data=None):
        """刷新表格显示"""
        data_to_show = filtered_data if filtered_data is not None else self.tasks_data
        print("data_to_show", data_to_show)
        self.table.setRowCount(0)

        for task in data_to_show:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            self.table.setItem(
                row_position, 0, QTableWidgetItem(str(task.get("id", "")))
            )
            self.table.setItem(
                row_position, 1, QTableWidgetItem(task.get("category", ""))
            )
            self.table.setItem(
                row_position, 2, QTableWidgetItem(task.get("subcategory", ""))
            )

            # 任务说明列添加 tooltip
            description_item = QTableWidgetItem(task.get("description", ""))
            description_item.setToolTip(task.get("description", ""))
            self.table.setItem(row_position, 3, description_item)

            # 处理特殊日期的显示
            due_date = task.get("due_date", "")
            if due_date == "1999-09-09":
                due_date_display = "无固定期限"
            elif due_date == "1999-09-10":
                due_date_display = "长期"
            else:
                due_date_display = due_date

            self.table.setItem(row_position, 4, QTableWidgetItem(due_date_display))
            self.table.setItem(
                row_position, 5, QTableWidgetItem(task.get("reminder_type", ""))
            )
            self.table.setItem(
                row_position, 6, QTableWidgetItem(task.get("reminder_time", ""))
            )

            # 状态列根据状态设置颜色
            status_item = QTableWidgetItem(task.get("status", ""))
            status = task.get("status", "")
            if status == "已完成":
                status_item.setBackground(QColor(0, 255, 0))  # 绿色
            elif status == "进行中":
                status_item.setBackground(QColor(255, 255, 0))  # 黄色
            elif status == "已取消":
                status_item.setBackground(QColor(128, 128, 128))  # 灰色

            self.table.setItem(row_position, 7, status_item)

            # 备注列添加 tooltip
            notes_item = QTableWidgetItem(task.get("notes", ""))
            notes_item.setToolTip(task.get("notes", ""))
            self.table.setItem(row_position, 8, notes_item)

    def apply_filters(self):
        """应用筛选条件"""
        # 获取选中的项目
        selected_categories = self.category_filter.get_selected()
        selected_subcategories = self.subcategory_filter.get_selected()
        selected_statuses = self.status_filter.get_selected()
        print("selected_categories", selected_categories)
        print("selected_subcategories", selected_subcategories)
        print("selected_statuses", selected_statuses)
        filtered = []
        for task in self.tasks_data:
            # 检查是否符合筛选条件（全选时不过滤）
            category_match = (task.get("category") in selected_categories) 
            subcategory_match = (task.get("subcategory") in selected_subcategories) 
            status_match = (task.get("status") in selected_statuses) 

            if category_match and subcategory_match and status_match:
                filtered.append(task)

        # 应用排序
        sorted_data = self.sort_data(filtered)
        self.refresh_table(sorted_data)

    def sort_data(self, data):
        """对数据进行排序"""
        sort_key = self.sort_combo.currentData()
        reverse = self.reverse_check.isChecked()

        if sort_key == "categories":
            # 按类别排序：先按大类，再按小类
            sorted_data = sorted(
                data,
                key=lambda x: (x.get("category", ""), x.get("subcategory", "")),
                reverse=reverse,
            )
        elif sort_key == "due":
            # 按截止期限排序
            def parse_date(task):
                due_date = task.get("due_date", "")
                try:
                    if " " in due_date:
                        return datetime.strptime(due_date, "%Y-%m-%d %H:%M")
                    else:
                        return datetime.strptime(due_date, "%Y-%m-%d")
                except:
                    return datetime.max  # 无法解析的日期排到最后

            sorted_data = sorted(data, key=parse_date, reverse=reverse)
        else:
            sorted_data = data

        return sorted_data

    def add_task(self, show_dialog=True):
        """添加新任务"""
        if show_dialog:
            dialog = TaskDialog(self)
            if dialog.exec() == int(QDialog.DialogCode.Accepted):
                task_data = dialog.get_task_data()

                # 生成新 ID
                max_id = max([t.get("id", 0) for t in self.tasks_data], default=0)
                new_id = max_id + 1
                task_data["id"] = new_id

                category = task_data.get("category", "")
                if category:
                    self.category_filter.items.append(category)
                subcategory = task_data.get("subcategory", "")
                if subcategory:
                    self.subcategory_filter.items.append(subcategory)

                self.tasks_data.append(task_data)
                self.save_tasks()
                self.save_categories()
                self.load_categories_to_filters()
                self.load_tasks()
                QMessageBox.information(self, "成功", "任务添加成功！")
        return True

    def edit_task(self):
        """编辑任务"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要编辑的任务！")
            return

        row = selected_rows[0].row()
        item = self.table.item(row, 0)
        if not item:
            return
        task_id = int(item.text())

        # 查找任务数据
        task_data = None
        for task in self.tasks_data:
            if task.get("id") == task_id:
                task_data = task.copy()
                break

        if task_data:
            dialog = TaskDialog(self, task_data)
            if dialog.exec() == int(QDialog.DialogCode.Accepted):
                updated_data = dialog.get_task_data()
                updated_data["id"] = task_id

                # 更新数据
                for i, task in enumerate(self.tasks_data):
                    if task.get("id") == task_id:
                        self.tasks_data[i] = updated_data
                        break

                self.save_tasks()
                self.load_tasks()
                QMessageBox.information(self, "成功", "任务更新成功！")

    def delete_task(self):
        """删除任务"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的任务！")
            return

        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除选中的任务吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            row = selected_rows[0].row()
            item = self.table.item(row, 0)
            if not item:
                return
            task_id = int(item.text())

            # 删除数据
            self.tasks_data = [t for t in self.tasks_data if t.get("id") != task_id]
            self.save_tasks()
            self.load_tasks()
            QMessageBox.information(self, "成功", "任务删除成功！")

    def mark_complete(self):
        """标记任务为完成"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要标记完成的任务！")
            return

        row = selected_rows[0].row()
        item = self.table.item(row, 0)
        if not item:
            return
        task_id = int(item.text())

        # 更新状态
        for i, task in enumerate(self.tasks_data):
            if task.get("id") == task_id:
                self.tasks_data[i]["status"] = "已完成"
                break

        self.save_tasks()
        self.load_tasks()
        QMessageBox.information(self, "成功", "任务已标记为完成！")

    def check_reminders(self):
        """检查是否需要提醒"""
        current_time = datetime.now()
        current_date_str = current_time.strftime("%Y-%m-%d")
        current_time_str = current_time.strftime("%H:%M")

        for task in self.tasks_data:
            if task.get("status") == "已完成":
                continue

            reminder_type = task.get("reminder_type", "")
            reminder_time_str = task.get("reminder_time", "")

            if not reminder_time_str:
                continue

            # 检查是否到达提醒时间
            if reminder_time_str != current_time_str:
                continue

            # 根据提醒类型判断是否需要提醒
            should_remind = False
            task_key = f"{task.get('id')}_{current_date_str}"

            if reminder_type == "每天":
                # 每天都提醒，只需要检查今天是否已经提醒过
                if task_key not in self.notified_tasks:
                    should_remind = True
                    self.notified_tasks[task_key] = True

            elif reminder_type == "当天":
                # 只在完成日期当天提醒
                due_date = task.get("due_date", "")
                if due_date:
                    try:
                        # 兼容旧格式（包含时间）和新格式（只有日期）
                        if " " in due_date:
                            due_date_obj = datetime.strptime(due_date, "%Y-%m-%d %H:%M")
                        else:
                            due_date_obj = datetime.strptime(due_date, "%Y-%m-%d")
                        due_date_str = due_date_obj.strftime("%Y-%m-%d")
                        if (
                            due_date_str == current_date_str
                            and task_key not in self.notified_tasks
                        ):
                            should_remind = True
                            self.notified_tasks[task_key] = True
                    except:
                        pass

            elif reminder_type == "仅一次":
                # 只提醒一次
                if task_key not in self.notified_tasks:
                    should_remind = True
                    self.notified_tasks[task_key] = True

            if should_remind:
                self.show_system_notification(task)

        # 清理过期的通知记录（保留今天的记录）
        self.notified_tasks = {
            k: v for k, v in self.notified_tasks.items() if current_date_str in k
        }

    def show_system_notification(self, task):
        """显示系统通知"""
        title = f"📋 任务提醒"
        message = f"【{task.get('category', '')} - {task.get('subcategory', '')}】\n{task.get('description', '')}\n\n完成期限：{task.get('due_date', '')}"

        try:
            # 使用 plyer 发送系统通知
            plyer.notification.notify(
                title=title,
                message=message,
                app_name="每日任务提醒器",
                timeout=10,  # 通知显示 10 秒
            )
        except Exception as e:
            print(f"系统通知失败：{e}")
            # 如果系统通知失败，回退到弹窗
            QMessageBox.information(self, title, message)

    def update_status(self):
        """更新状态栏"""
        total = len(self.tasks_data)
        completed = sum(1 for t in self.tasks_data if t.get("status") == "已完成")
        incomplete = total - completed

        self.status_label.setText(
            f"总任务数：{total} | 未完成：{incomplete} | 已完成：{completed}"
        )

    # ==================== API 接口方法（暴露给其他插件调用） ====================

    def add_task_api(self, task_data: dict) -> int:
        """
        API: 添加任务

        Args:
            task_data: 任务数据字典，包含以下字段：
                - category: 任务大类
                - subcategory: 任务小类
                - description: 任务说明
                - due_date: 完成日期 (格式：yyyy-MM-dd)
                - reminder_type: 提醒方式 (每天/当天/仅一次)
                - reminder_time: 提醒时间 (格式：HH:mm)
                - status: 完成状态 (未完成/已完成/进行中/已取消)
                - notes: 备注

        Returns:
            int: 新任务的 ID，如果失败返回 -1
        """
        try:
            # 生成新 ID
            max_id = max([t.get("id", 0) for t in self.tasks_data], default=0)
            new_id = max_id + 1

            # 创建任务数据
            new_task = {
                "id": new_id,
                "category": task_data.get("category", ""),
                "subcategory": task_data.get("subcategory", ""),
                "description": task_data.get("description", ""),
                "due_date": task_data.get("due_date", ""),
                "reminder_type": task_data.get("reminder_type", "仅一次"),
                "reminder_time": task_data.get("reminder_time", ""),
                "status": task_data.get("status", "未完成"),
                "notes": task_data.get("notes", ""),
            }

            # 添加到数据列表
            self.tasks_data.append(new_task)
            self.save_tasks()

            # 更新分类
            category = new_task.get("category", "")
            if category and category not in self.category_filter.items:
                self.category_filter.items.append(category)
            subcategory = new_task.get("subcategory", "")
            if subcategory and subcategory not in self.subcategory_filter.items:
                self.subcategory_filter.items.append(subcategory)

            self.save_categories()
            self.load_categories_to_filters()
            self.load_tasks()

            return new_id
        except Exception as e:
            print(f"[DailyTasks] 添加任务失败：{e}")
            import traceback
            traceback.print_exc()
            return -1

    def delete_task_api(self, task_id: int) -> bool:
        """
        API: 删除任务

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否删除成功
        """
        try:
            # 查找任务
            task_exists = any(t.get("id") == task_id for t in self.tasks_data)
            if not task_exists:
                return False

            # 删除任务
            self.tasks_data = [t for t in self.tasks_data if t.get("id") != task_id]
            self.save_tasks()
            self.load_tasks()
            return True
        except Exception as e:
            print(f"[DailyTasks] 删除任务失败：{e}")
            return False

    def get_tasks_api(self, filters: dict = None) -> list:
        """
        API: 获取任务列表

        Args:
            filters: 过滤条件（可选），支持：
                - category: 任务大类（字符串或列表）
                - subcategory: 任务小类（字符串或列表）
                - status: 完成状态（字符串或列表）
                - due_date_from: 开始日期 (格式：yyyy-MM-dd)
                - due_date_to: 结束日期 (格式：yyyy-MM-dd)

        Returns:
            list: 任务列表
        """
        try:
            if not filters:
                return self.tasks_data.copy()

            filtered = []
            for task in self.tasks_data:
                # 检查大类
                if "category" in filters:
                    filter_cat = filters["category"]
                    if isinstance(filter_cat, str):
                        filter_cat = [filter_cat]
                    if task.get("category") not in filter_cat:
                        continue

                # 检查小类
                if "subcategory" in filters:
                    filter_subcat = filters["subcategory"]
                    if isinstance(filter_subcat, str):
                        filter_subcat = [filter_subcat]
                    if task.get("subcategory") not in filter_subcat:
                        continue

                # 检查状态
                if "status" in filters:
                    filter_status = filters["status"]
                    if isinstance(filter_status, str):
                        filter_status = [filter_status]
                    if task.get("status") not in filter_status:
                        continue

                # 检查日期范围
                if "due_date_from" in filters or "due_date_to" in filters:
                    due_date = task.get("due_date", "")
                    if due_date:
                        if "due_date_from" in filters:
                            if due_date < filters["due_date_from"]:
                                continue
                        if "due_date_to" in filters:
                            if due_date > filters["due_date_to"]:
                                continue

                filtered.append(task)

            return filtered
        except Exception as e:
            print(f"[DailyTasks] 获取任务列表失败：{e}")
            return []

    def get_task_by_id_api(self, task_id: int) -> dict:
        """
        API: 根据 ID 获取任务

        Args:
            task_id: 任务 ID

        Returns:
            dict: 任务数据，不存在返回 None
        """
        try:
            for task in self.tasks_data:
                if task.get("id") == task_id:
                    return task.copy()
            return None
        except Exception as e:
            print(f"[DailyTasks] 获取任务失败：{e}")
            return None

    def update_task_api(self, task_id: int, task_data: dict) -> bool:
        """
        API: 更新任务

        Args:
            task_id: 任务 ID
            task_data: 新的任务数据

        Returns:
            bool: 是否更新成功
        """
        try:
            # 查找任务
            for i, task in enumerate(self.tasks_data):
                if task.get("id") == task_id:
                    # 保留 ID
                    updated_task = task.copy()
                    updated_task.update(task_data)
                    updated_task["id"] = task_id
                    self.tasks_data[i] = updated_task
                    self.save_tasks()
                    self.load_tasks()
                    return True
            return False
        except Exception as e:
            print(f"[DailyTasks] 更新任务失败：{e}")
            return False

    def filter_tasks_by_date_api(
        self, start_date: str, end_date: str = None
    ) -> list:
        """
        API: 按日期过滤任务

        Args:
            start_date: 开始日期 (格式：yyyy-MM-dd)
            end_date: 结束日期（可选，格式：yyyy-MM-dd），不提供则只过滤当天的

        Returns:
            list: 任务列表
        """
        try:
            if end_date is None:
                end_date = start_date

            filtered = []
            for task in self.tasks_data:
                due_date = task.get("due_date", "")
                if due_date and start_date <= due_date <= end_date:
                    filtered.append(task)

            return filtered
        except Exception as e:
            print(f"[DailyTasks] 按日期过滤任务失败：{e}")
            return []

    def mark_task_complete_api(self, task_id: int) -> bool:
        """
        API: 标记任务为完成

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否成功
        """
        try:
            for i, task in enumerate(self.tasks_data):
                if task.get("id") == task_id:
                    self.tasks_data[i]["status"] = "已完成"
                    self.save_tasks()
                    self.load_tasks()
                    return True
            return False
        except Exception as e:
            print(f"[DailyTasks] 标记任务完成失败：{e}")
            return False


# ==================== 插件入口函数 ====================


def load_plugin(plugin_manager):
    """
    插件加载入口函数

    Args:
        plugin_manager: 插件管理器实例

    Returns:
        dict: 包含插件组件的字典
    """
    print("[DailyTasks] 正在加载每日任务提醒器插件...")

    # 创建标签页实例
    tasks_tab = TasksManagerTab(plugin_manager=plugin_manager)

    # 注册暴露的方法到全局域
    plugin_manager.register_method(
        "daily_tasks", "add_task", tasks_tab.add_task_api
    )
    plugin_manager.register_method(
        "daily_tasks", "delete_task", tasks_tab.delete_task_api
    )
    plugin_manager.register_method(
        "daily_tasks", "get_tasks", tasks_tab.get_tasks_api
    )
    plugin_manager.register_method(
        "daily_tasks", "get_task_by_id", tasks_tab.get_task_by_id_api
    )
    plugin_manager.register_method(
        "daily_tasks", "update_task", tasks_tab.update_task_api
    )
    plugin_manager.register_method(
        "daily_tasks", "filter_tasks_by_date", tasks_tab.filter_tasks_by_date_api
    )
    plugin_manager.register_method(
        "daily_tasks", "mark_task_complete", tasks_tab.mark_task_complete_api
    )

    # 添加到标签页（由插件管理器统一管理）
    plugin_manager.add_plugin_tab("daily_tasks", "📋 任务管理", tasks_tab, position=1)

    print("[DailyTasks] 每日任务提醒器插件加载完成")
    return {"tab": tasks_tab, "namespace": "daily_tasks"}


def unload_plugin(plugin_manager):
    """
    插件卸载回调

    Args:
        plugin_manager: 插件管理器实例
    """
    print("[DailyTasks] 正在卸载每日任务提醒器插件...")
    # 清理资源、保存状态等
    print("[DailyTasks] 每日任务提醒器插件卸载完成")
