"""
文本处理插件 - 提供多种文本转换和剪贴板管理功能
迁移自 tabs/text_helper.py
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QTextEdit,
    QListWidget,
    QPushButton,
    QLabel,
    QFrame,
    QGroupBox,
    QMenuBar,
    QApplication,
    QDialog,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QAction, QKeySequence
import pyperclip
import re
import os
import tempfile
import subprocess
import logging

logger = logging.getLogger(__name__)

# Initialize plugin i18n
from app_qt.plugin_i18n import PluginI18n
_i18n = PluginI18n("text_helper", Path(__file__).parent)
_ = _i18n.gettext


class TextHelperTab(QWidget):
    """文本处理标签页"""

    def __init__(self, clipboard_callback=None):
        super().__init__()
        self.clipboard_callback = clipboard_callback
        self.clipboard_history = []
        self.max_clipboard_history = 50

        # 存储自定义菜单项的引用，便于后续管理
        self.custom_actions = []

        # 存储自定义菜单的引用
        self.custom_menus = {}

        self.init_ui()
        self.load_initial_clipboard()

        # 启动剪贴板监控定时器
        self.clipboard_timer = QTimer()
        self.clipboard_timer.timeout.connect(self.check_clipboard)
        self.clipboard_timer.start(1000)  # 每 1 秒检查一次
        self.last_clipboard = ""

    def init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # 创建顶部菜单栏
        self.menubar = QMenuBar()
        main_layout.setMenuBar(self.menubar)

        # 创建文本处理菜单
        self.text_menu = self.menubar.addMenu(_("Text Processing") + " (&T)")

        # 添加默认菜单项到文本处理菜单
        self.remove_newlines_action = QAction(_("Remove Newlines"), self)
        self.remove_newlines_action.setShortcut(QKeySequence("Ctrl+Alt+L"))
        self.remove_newlines_action.triggered.connect(self.remove_newlines)
        self.text_menu.addAction(self.remove_newlines_action)

        self.double_newlines_action = QAction(_("Add Double Newlines"), self)
        self.double_newlines_action.setShortcut(QKeySequence("Ctrl+Alt+D"))
        self.double_newlines_action.triggered.connect(self.add_double_newlines)
        self.text_menu.addAction(self.double_newlines_action)

        self.remove_illegal_action = QAction(_("Remove Illegal Chars"), self)
        self.remove_illegal_action.setShortcut(QKeySequence("Ctrl+Alt+I"))
        self.remove_illegal_action.triggered.connect(self.remove_illegal_chars)
        self.text_menu.addAction(self.remove_illegal_action)

        self.remove_filename_action = QAction(_("Remove Filename Illegal Chars"), self)
        self.remove_filename_action.setShortcut(QKeySequence("Ctrl+Alt+F"))
        self.remove_filename_action.triggered.connect(
            self.remove_filename_illegal_chars
        )
        self.text_menu.addAction(self.remove_filename_action)

        self.text_menu.addSeparator()

        self.copy_action = QAction(_("Copy Result"), self)
        self.copy_action.setShortcut(QKeySequence("Ctrl+C"))
        self.copy_action.triggered.connect(self.copy_to_clipboard)
        self.text_menu.addAction(self.copy_action)

        # 创建中央分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧：文本处理区域
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)

        # 输入文本框
        input_group = QGroupBox(_("Input Text"))
        input_layout = QVBoxLayout()
        input_group.setLayout(input_layout)

        self.text_input = QTextEdit()
        self.text_input.setFont(QFont("Consolas", 10))
        self.text_input.setPlaceholderText(_("Enter or paste text here..."))
        self.text_input.setUndoRedoEnabled(True)  # 启用撤销/重做功能
        input_layout.addWidget(self.text_input)

        left_layout.addWidget(input_group)

        splitter.addWidget(left_widget)

        # 右侧：剪贴板历史
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)

        clipboard_group = QGroupBox("📋 " + _("Clipboard History"))
        clipboard_layout = QVBoxLayout()
        clipboard_group.setLayout(clipboard_layout)

        self.clipboard_list = QListWidget()
        self.clipboard_list.setFont(QFont("Consolas", 9))
        self.clipboard_list.itemDoubleClicked.connect(self.load_clipboard_item)
        clipboard_layout.addWidget(self.clipboard_list)

        self.clear_history_btn = QPushButton(_("Clear History"))
        self.clear_history_btn.clicked.connect(self.clear_clipboard_history)
        clipboard_layout.addWidget(self.clear_history_btn)

        right_layout.addWidget(clipboard_group)
        splitter.addWidget(right_widget)

        # 设置分割器比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([600, 250])

    # ==================== API 接口方法（暴露给其他插件调用） ====================

    def get_text_api(self):
        """
        API: 获取当前输入框中的文本

        Returns:
            str: 当前输入框中的文本
        """
        return self.text_input.toPlainText()

    def set_text_api(self, text):
        """
        API: 设置输入框中的文本

        Args:
            text: 要设置的文本

        Returns:
            bool: 是否设置成功
        """
        try:
            self.text_input.setPlainText(text)
            return True
        except Exception as e:
            print(_("[TextHelper] Failed to set text: {}") + str(e))
            return False

    def add_menu_to_menubar_api(self, menu):
        """
        API: 将 QMenu组件添加到菜单栏

        Args:
            menu: QMenu组件实例

        Returns:
            bool: 是否添加成功
        """
        try:

            # 将传入的菜单添加到菜单栏
            self.menubar.addMenu(menu)

            # 保存菜单引用（使用菜单对象作为 key）
            self.custom_menus[id(menu)] = menu

            print(_("[TextHelper] Menu added to menubar"))
            return True

        except Exception as e:
            print(_("[TextHelper] Failed to add menu: {}") + str(e))
            import traceback

            traceback.print_exc()
            return False

    def register_text_action_api(self, name, callback, shortcut=None):
        """
        API: 注册自定义文本处理菜单项

        Args:
            name: 菜单项名称
            callback: 回调函数，接收当前文本作为参数，返回处理后的文本
            shortcut: 快捷键（可选），如 'Ctrl+Alt+X'

        Returns:
            bool: 是否注册成功
        """
        try:
            # 创建菜单项
            action = QAction(name, self)

            # 设置快捷键（如果提供）
            if shortcut:
                try:
                    action.setShortcut(QKeySequence(shortcut))
                except Exception as e:
                    print(_("[TextHelper] Failed to set shortcut: {}") + str(e))

            # 绑定回调函数
            def on_triggered():
                current_text = self.text_input.toPlainText()
                try:
                    result = callback(current_text)
                    if result and isinstance(result, str):
                        self.text_input.setPlainText(result)
                except Exception as e:
                    print(_("[TextHelper] Custom handler failed: {}") + str(e))
                    import traceback

                    traceback.print_exc()

            action.triggered.connect(on_triggered)
            self.text_menu.addAction(action)

            # 保存引用
            self.custom_actions.append(action)

            print(_("[TextHelper] Registered custom menu item: {}") + name)
            return True

        except Exception as e:
            print(f"[TextHelper] 注册自定义菜单项失败：{e}")
            return False

    def remove_newlines_api(self, text):
        """
        API: 去除换行符

        Args:
            text: 输入文本

        Returns:
            str: 处理后的文本
        """
        return text.replace("\n", " ").replace("\r", " ")

    def add_double_newlines_api(self, text):
        """
        API: 添加双重换行符

        Args:
            text: 输入文本

        Returns:
            str: 处理后的文本
        """
        return text.replace("\n", "\n\n").replace("\r", "\r\r")

    def remove_illegal_chars_api(self, text):
        """
        API: 去除非法字符

        Args:
            text: 输入文本

        Returns:
            str: 处理后的文本
        """
        result = "".join(
            char for char in text if char.isprintable() or char in "\n\r\t "
        )
        result = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", result)
        return result

    def remove_filename_illegal_chars_api(self, text):
        """
        API: 去除文件名非法字符

        Args:
            text: 输入文本

        Returns:
            str: 处理后的文本
        """
        allowed_chars = []
        for char in text:
            if char.isalnum():
                allowed_chars.append(char)
            elif char in "-_() ":
                allowed_chars.append(char)
            elif char.isspace():
                allowed_chars.append(" ")

        return "".join(allowed_chars)

    def load_initial_clipboard(self):
        """加载初始剪贴板内容"""
        try:
            initial_content = pyperclip.paste()
            if initial_content:
                self.add_to_clipboard_history(initial_content)
        except:
            pass

    def add_double_newlines(self):
        """添加双重换行符"""
        content = self.text_input.toPlainText()
        result = content.replace("\n", "\n\n").replace("\r", "\r\r")
        self.text_input.setPlainText(result)

    def remove_newlines(self):
        """去除换行符"""
        content = self.text_input.toPlainText()
        result = content.replace("\n", " ").replace("\r", " ")
        self.text_input.setPlainText(result)

    def remove_illegal_chars(self):
        """去除非法字符"""
        content = self.text_input.toPlainText()
        result = "".join(
            char for char in content if char.isprintable() or char in "\n\r\t "
        )
        result = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", result)
        self.text_input.setPlainText(result)

    def remove_filename_illegal_chars(self):
        """去除文件名非法字符"""
        content = self.text_input.toPlainText()
        allowed_chars = []
        for char in content:
            if char.isalnum():
                allowed_chars.append(char)
            elif char in "-_() ":
                allowed_chars.append(char)
            elif char.isspace():
                allowed_chars.append(" ")

        result = "".join(allowed_chars)
        self.text_input.setPlainText(result)

    def copy_to_clipboard(self):
        """复制内容到剪贴板"""
        text = self.text_input.toPlainText().strip()
        if not text:
            return

        try:
            pyperclip.copy(text)
        except:
            pass

    def add_to_clipboard_history(self, text):
        """添加文本到剪贴板历史"""
        if not text or text.strip() == "":
            return

        if text in self.clipboard_history:
            self.clipboard_history.remove(text)

        self.clipboard_history.insert(0, text)

        if len(self.clipboard_history) > self.max_clipboard_history:
            self.clipboard_history.pop()

        self.update_clipboard_list()

        if self.clipboard_callback:
            self.clipboard_callback(text)

    def update_clipboard_list(self):
        """更新剪贴板历史列表显示"""
        self.clipboard_list.clear()

        for i, item in enumerate(self.clipboard_history):
            display_text = item[:50].replace("\n", "↵").replace("\r", "")
            if len(item) > 50:
                display_text += "..."
            self.clipboard_list.addItem(f"[{i+1}] {display_text}")

    def load_clipboard_item(self, item):
        """双击加载剪贴板历史项"""
        index = self.clipboard_list.row(item)
        if 0 <= index < len(self.clipboard_history):
            text = self.clipboard_history[index]
            self.text_input.setPlainText(text)

    def clear_clipboard_history(self):
        """清空剪贴板历史"""
        self.clipboard_history.clear()
        self.update_clipboard_list()

    def check_clipboard(self):
        """检查剪贴板变化"""
        try:
            current = pyperclip.paste()
            if current and current != self.last_clipboard:
                self.last_clipboard = current
                self.add_to_clipboard_history(current)
        except:
            pass

    def _send_to_editor(self, text):
        """
        Send text to main editor
        
        Args:
            text: Text content to send
        """
        self.text_input.setPlainText(text)
        print(_("[TextHelper] Sent {} characters to editor").format(len(text)))


# ==================== 插件入口函数 ====================


def load_plugin(plugin_manager):
    """
    插件加载入口函数

    Args:
        plugin_manager: 插件管理器实例

    Returns:
        dict: 包含插件组件的字典
    """
    print("[TextHelper] 正在加载文本处理插件...")

    # 创建标签页实例
    text_tab = TextHelperTab(clipboard_callback=None)

    # 注册暴露的方法到全局域
    plugin_manager.register_method(
        "text_helper", "add_menu_to_menubar", text_tab.add_menu_to_menubar_api
    )
    plugin_manager.register_method(
        "text_helper", "register_text_action", text_tab.register_text_action_api
    )
    plugin_manager.register_method("text_helper", "get_text", text_tab.get_text_api)
    plugin_manager.register_method("text_helper", "set_text", text_tab.set_text_api)

    # 添加到标签页（由插件管理器统一管理）
    plugin_manager.add_plugin_tab("text_helper", _("📝 Text Processing"), text_tab, position=0)

    print("[TextHelper] 文本处理插件加载完成")
    return {"tab": text_tab, "namespace": "text_helper"}


def unload_plugin(plugin_manager):
    """
    插件卸载回调

    Args:
        plugin_manager: 插件管理器实例
    """
    print("[TextHelper] 正在卸载文本处理插件...")
    # 清理资源、保存状态等
    print("[TextHelper] 文本处理插件卸载完成")
