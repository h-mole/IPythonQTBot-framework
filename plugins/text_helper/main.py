"""
文本处理插件 - 提供多种文本转换和剪贴板管理功能
迁移自 tabs/text_helper.py
"""

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

# 导入 Markdown 渲染组件
try:
    from QMarkdownView import MarkdownView, LinkMiddlewarePolicy
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False
    print("[TextHelper] 警告：未找到 QMarkdownView，Markdown 渲染功能将不可用")


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
        self.text_menu = self.menubar.addMenu("文本处理 (&T)")

        # 添加默认菜单项到文本处理菜单
        self.remove_newlines_action = QAction("去除换行符", self)
        self.remove_newlines_action.setShortcut(QKeySequence("Ctrl+Alt+L"))
        self.remove_newlines_action.triggered.connect(self.remove_newlines)
        self.text_menu.addAction(self.remove_newlines_action)

        self.double_newlines_action = QAction("添加双重换行符", self)
        self.double_newlines_action.setShortcut(QKeySequence("Ctrl+Alt+D"))
        self.double_newlines_action.triggered.connect(self.add_double_newlines)
        self.text_menu.addAction(self.double_newlines_action)

        self.remove_illegal_action = QAction("去除非法字符", self)
        self.remove_illegal_action.setShortcut(QKeySequence("Ctrl+Alt+I"))
        self.remove_illegal_action.triggered.connect(self.remove_illegal_chars)
        self.text_menu.addAction(self.remove_illegal_action)

        self.remove_filename_action = QAction("去除文件名非法字符", self)
        self.remove_filename_action.setShortcut(QKeySequence("Ctrl+Alt+F"))
        self.remove_filename_action.triggered.connect(
            self.remove_filename_illegal_chars
        )
        self.text_menu.addAction(self.remove_filename_action)

        self.text_menu.addSeparator()

        # 添加 Markdown 渲染菜单项
        if HAS_MARKDOWN:
            self.markdown_render_action = QAction("📄 渲染 Markdown", self)
            self.markdown_render_action.setShortcut(QKeySequence("Ctrl+Alt+M"))
            self.markdown_render_action.triggered.connect(lambda *args: self.show_markdown_preview())
            self.text_menu.addAction(self.markdown_render_action)
            self.text_menu.addSeparator()

        self.copy_action = QAction("复制结果", self)
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
        input_group = QGroupBox("输入文本")
        input_layout = QVBoxLayout()
        input_group.setLayout(input_layout)

        self.text_input = QTextEdit()
        self.text_input.setFont(QFont("Consolas", 10))
        self.text_input.setPlaceholderText("在此输入或粘贴文本...")
        self.text_input.setUndoRedoEnabled(True)  # 启用撤销/重做功能
        input_layout.addWidget(self.text_input)

        left_layout.addWidget(input_group)

        splitter.addWidget(left_widget)

        # 右侧：剪贴板历史
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)

        clipboard_group = QGroupBox("📋 剪贴板历史")
        clipboard_layout = QVBoxLayout()
        clipboard_group.setLayout(clipboard_layout)

        self.clipboard_list = QListWidget()
        self.clipboard_list.setFont(QFont("Consolas", 9))
        self.clipboard_list.itemDoubleClicked.connect(self.load_clipboard_item)
        clipboard_layout.addWidget(self.clipboard_list)

        self.clear_history_btn = QPushButton("清空历史")
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
            print(f"[TextHelper] 设置文本失败：{e}")
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

            print(f"[TextHelper] 已添加菜单到菜单栏")
            return True

        except Exception as e:
            print(f"[TextHelper] 添加菜单失败：{e}")
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
                    print(f"[TextHelper] 设置快捷键失败：{e}")

            # 绑定回调函数
            def on_triggered():
                current_text = self.text_input.toPlainText()
                try:
                    result = callback(current_text)
                    if result and isinstance(result, str):
                        self.text_input.setPlainText(result)
                except Exception as e:
                    print(f"[TextHelper] 自定义处理函数执行失败：{e}")
                    import traceback

                    traceback.print_exc()

            action.triggered.connect(on_triggered)
            self.text_menu.addAction(action)

            # 保存引用
            self.custom_actions.append(action)

            print(f"[TextHelper] 已注册自定义菜单项：{name}")
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

    def render_markdown_api(self, text=None):
        """
        API: 渲染 Markdown 文本并显示预览窗口

        Args:
            text: 可选参数，如果不传则使用输入框中的文本

        Returns:
            bool: 是否成功显示预览窗口
        """
        return self.show_markdown_preview(text)

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
        将文本发送到主编辑控件
        
        Args:
            text: 要发送的文本内容
        """
        self.text_input.setPlainText(text)
        print(f"[TextHelper] 已将 {len(text)} 字符的内容发送到编辑器")

    def show_markdown_preview(self, text=None):
        """
        显示 Markdown 预览窗口
        
        Args:
            text: 可选参数，如果不传则使用输入框中的文本
        """
        if not HAS_MARKDOWN:
            print("[TextHelper] Markdown 渲染功能不可用")
            return False

        try:
            # 获取当前输入框中的文本（如果没有传入 text）
            if text is None:
                markdown_text = self.text_input.toPlainText()
            else:
                markdown_text = text
            
            if not markdown_text.strip():
                print("[TextHelper] 没有可渲染的 Markdown 内容")
                return False

            # 创建预览对话框
            self.preview_dialog = QDialog(self)
            self.preview_dialog.setWindowTitle("Markdown 预览")
            self.preview_dialog.resize(800, 600)

            # 设置布局
            layout = QVBoxLayout()
            self.preview_dialog.setLayout(layout)

            # 创建 Markdown 视图
            markdown_view = MarkdownView()
            markdown_view.setExtensions([
                "markdown.extensions.tables",
                "markdown.extensions.extra",
                "markdown.extensions.codehilite",
                "markdown.extensions.toc"
            ])
            markdown_view.loadFinished.connect(lambda: markdown_view.setValue(markdown_text))
            # 设置 Markdown 内容
            

            # 添加到布局
            layout.addWidget(markdown_view)

            # 创建按钮区域
            button_layout = QHBoxLayout()

            # 发送到编辑器按钮 - 将原始内容发送到主编辑控件
            send_btn = QPushButton("发送到编辑器")
            send_btn.clicked.connect(lambda: self._send_to_editor(markdown_text))
            button_layout.addWidget(send_btn)

            # 刷新按钮
            refresh_btn = QPushButton("刷新")
            refresh_btn.clicked.connect(lambda: markdown_view.setValue(self.text_input.toPlainText() if text is None else text))
            button_layout.addWidget(refresh_btn)

            # 关闭按钮
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(self.preview_dialog.close)
            button_layout.addWidget(close_btn)

            button_layout.addStretch()

            layout.addLayout(button_layout)

            # 显示对话框
            self.preview_dialog.exec_()

            print("[TextHelper] Markdown 预览已关闭")
            return True

        except Exception as e:
            print(f"[TextHelper] Markdown 渲染失败：{e}")
            import traceback
            traceback.print_exc()
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
    plugin_manager.register_method("text_helper", "render_markdown", text_tab.render_markdown_api)

    # 添加到标签页（由插件管理器统一管理）
    plugin_manager.add_plugin_tab("text_helper", "📝 文本处理", text_tab, position=0)

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
