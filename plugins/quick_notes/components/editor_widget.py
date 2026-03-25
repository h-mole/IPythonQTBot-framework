"""
快速笔记插件 - 编辑器组件
提供文本编辑、查找替换等功能
"""

from PySide6.QtWidgets import (
    QTextEdit,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLineEdit,
    QLabel,
    QMessageBox,
    QMenu,
    QApplication,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeySequence, QAction
import os
from ..syntaxedit.core import SyntaxEdit
from pygments.lexers import get_lexer_for_filename


class EditorToolbar(QFrame):
    """编辑器工具栏组件"""

    # 信号：保存、查找、替换等操作
    save_requested = Signal()
    find_requested = Signal()
    replace_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        self.init_ui()
        self._is_modified = False
        self._current_full_path = None
        self._current_rel_path = None

    def init_ui(self):
        """初始化界面"""
        layout = QHBoxLayout()
        self.setLayout(layout)

        # 保存按钮
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(lambda: self.save_requested.emit())
        layout.addWidget(self.save_btn)

        # 查找按钮
        self.find_btn = QPushButton("🔍 查找")
        self.find_btn.clicked.connect(lambda: self.find_requested.emit())
        layout.addWidget(self.find_btn)

        # 替换按钮
        self.replace_btn = QPushButton("🔄 替换")
        self.replace_btn.clicked.connect(lambda: self.replace_requested.emit())
        layout.addWidget(self.replace_btn)

        layout.addStretch()

        # 保存状态标签
        self.save_status_label = QLabel("")
        self.save_status_label.setFont(QFont("Consolas", 9))
        layout.addWidget(self.save_status_label)

        # 当前文件路径显示（可点击复制）
        self.current_path_label = QLabel("")
        self.current_path_label.setFont(QFont("Consolas", 8))
        self.current_path_label.setStyleSheet("""
            QLabel {
                color: gray;
                padding: 2px 6px;
                border-radius: 3px;
            }
            QLabel:hover {
                background-color: #e8e8e8;
                color: #333;
            }
        """)
        self.current_path_label.setCursor(Qt.PointingHandCursor)
        self.current_path_label.setToolTip("点击复制路径")
        self.current_path_label.mousePressEvent = self._on_path_label_clicked
        layout.addWidget(self.current_path_label)

    def _on_path_label_clicked(self, event):
        """路径标签点击事件 - 复制相对路径到剪贴板"""
        if self._current_rel_path:
            clipboard = QApplication.clipboard()
            clipboard.setText(self._current_rel_path)
            # 临时改变文本提示已复制
            original_text = self.current_path_label.text()
            self.current_path_label.setText("✓ 已复制")
            # 使用 QTimer 恢复原始文本
            from PySide6.QtCore import QTimer
            QTimer.singleShot(800, lambda: self.current_path_label.setText(original_text))

    def update_current_path(self, file_path, notes_dir=None):
        """更新当前文件路径显示

        Args:
            file_path: 文件完整路径
            notes_dir: 笔记根目录路径，用于计算相对路径
        """
        MAX_PATHLEN = 60
        if file_path:
            # 保存完整路径
            self._current_full_path = file_path
            
            # 转换为相对路径
            if notes_dir:
                rel_path = os.path.relpath(file_path, notes_dir)
            else:
                rel_path = file_path
            
            # 保存相对路径
            self._current_rel_path = rel_path

            # 如果路径超过 MAX_PATHLEN 字符，从左侧截断，保留右侧
            display_path = rel_path
            if len(display_path) > MAX_PATHLEN:
                display_path = "..." + display_path[-(MAX_PATHLEN - 3) :]

            self.current_path_label.setText(f"📄 {display_path}")
            self.current_path_label.setToolTip(f"点击复制: {rel_path}")
        else:
            self.current_path_label.setText("")
            self.current_path_label.setToolTip("点击复制路径")
            self._current_full_path = None
            self._current_rel_path = None

    def set_save_status(self, is_modified):
        """设置保存状态显示

        Args:
            is_modified: 是否有未保存的修改
        """
        self._is_modified = is_modified
        if is_modified:
            self.save_status_label.setText("● 未保存")
            self.save_status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.save_btn.setEnabled(True)
        else:
            self.save_status_label.setText("✓ 已保存")
            self.save_status_label.setStyleSheet("color: #27ae60;")
            self.save_btn.setEnabled(False)

    def is_modified(self):
        """返回当前是否有未保存的修改"""
        return self._is_modified


class FindReplacePanel(QFrame):
    """查找替换面板组件"""

    # 信号：查找、替换操作
    find_next_requested = Signal(str)
    replace_one_requested = Signal(str, str)
    replace_all_requested = Signal(str, str)
    close_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setVisible(False)

        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # 查找行
        find_row = QHBoxLayout()
        find_label = QLabel("查找:")
        find_row.addWidget(find_label)

        self.find_input = QLineEdit()
        self.find_input.returnPressed.connect(self.on_find_next)
        find_row.addWidget(self.find_input)

        self.find_next_btn = QPushButton("查找下一个")
        self.find_next_btn.clicked.connect(self.on_find_next)
        find_row.addWidget(self.find_next_btn)

        self.find_close_btn = QPushButton("关闭")
        self.find_close_btn.clicked.connect(lambda: self.close_requested.emit())
        find_row.addWidget(self.find_close_btn)

        layout.addLayout(find_row)

        # 替换行
        replace_row = QHBoxLayout()
        replace_label = QLabel("替换:")
        replace_row.addWidget(replace_label)

        self.replace_input = QLineEdit()
        replace_row.addWidget(self.replace_input)

        self.replace_one_btn = QPushButton("替换")
        self.replace_one_btn.clicked.connect(self.on_replace_one)
        replace_row.addWidget(self.replace_one_btn)

        self.replace_all_btn = QPushButton("全部替换")
        self.replace_all_btn.clicked.connect(self.on_replace_all)
        replace_row.addWidget(self.replace_all_btn)

        layout.addLayout(replace_row)

    def on_find_next(self):
        """查找下一个"""
        search_term = self.find_input.text()
        if search_term:
            self.find_next_requested.emit(search_term)

    def on_replace_one(self):
        """替换一个"""
        search_term = self.find_input.text()
        replace_term = self.replace_input.text()
        if search_term:
            self.replace_one_requested.emit(search_term, replace_term)

    def on_replace_all(self):
        """全部替换"""
        search_term = self.find_input.text()
        replace_term = self.replace_input.text()
        if search_term:
            self.replace_all_requested.emit(search_term, replace_term)


class TextEditorWidget(SyntaxEdit):
    """文本编辑器组件"""

    # 信号：文本变化、保存请求
    text_changed = Signal()
    context_menu_requested = Signal()
    save_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setFont(QFont("Consolas", 10))
        self.setPlaceholderText("在此输入笔记内容...")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.textChanged.connect(lambda: self.text_changed.emit())

    def set_syntax_by_filepath(self, file_path):
        """根据文件路径设置语法高亮"""
        lexer = get_lexer_for_filename(file_path, guess=True)
        if lexer.name.lower() != "text only":
            self.setSyntax(lexer.name)

    def show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu(self)

        # 撤销/重做
        undo_action = menu.addAction("↶ 撤销")
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self.undo)
        undo_action.setEnabled(self.document().isUndoAvailable())

        redo_action = menu.addAction("↷ 重做")
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self.redo)
        redo_action.setEnabled(self.document().isRedoAvailable())

        menu.addSeparator()

        # 剪切/复制/粘贴
        cut_action = menu.addAction("✂ 剪切")
        cut_action.setShortcut(QKeySequence.Cut)
        cut_action.triggered.connect(self.cut)
        cut_action.setEnabled(self.textCursor().hasSelection())

        copy_action = menu.addAction("📋 复制")
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.copy)
        copy_action.setEnabled(self.textCursor().hasSelection())

        paste_action = menu.addAction("📌 粘贴")
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(self.paste)

        menu.addSeparator()

        # 全选
        select_all_action = menu.addAction("☑ 全选")
        select_all_action.setShortcut(QKeySequence.SelectAll)
        select_all_action.triggered.connect(self.selectAll)

        menu.addSeparator()

        # 查找/替换
        find_action = menu.addAction("🔍 查找")
        find_action.setShortcut(QKeySequence.Find)
        find_action.triggered.connect(
            lambda: self.parent().parent().find_requested.emit()
        )

        replace_action = menu.addAction("🔄 替换")
        replace_action.setShortcut(QKeySequence.Replace)
        replace_action.triggered.connect(
            lambda: self.parent().parent().replace_requested.emit()
        )

        menu.addSeparator()

        # 保存
        save_action = menu.addAction("💾 保存")
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_requested.emit)

        menu.exec_(self.viewport().mapToGlobal(pos))
