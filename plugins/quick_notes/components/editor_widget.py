"""
快速笔记插件 - 编辑器组件
提供文本编辑、查找替换等功能
"""

from PySide6.QtWidgets import (
    QTextEdit, QFrame, QHBoxLayout, QVBoxLayout, 
    QPushButton, QLineEdit, QLabel, QMessageBox, QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeySequence, QAction


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
        
        # 当前文件路径显示
        self.current_path_label = QLabel("")
        self.current_path_label.setFont(QFont("Consolas", 8))
        self.current_path_label.setStyleSheet("color: gray;")
        layout.addWidget(self.current_path_label)
    
    def update_current_path(self, file_path):
        """更新当前文件路径显示"""
        if file_path:
            self.current_path_label.setText(f"📄 {file_path}")
        else:
            self.current_path_label.setText("")


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


class TextEditorWidget(QTextEdit):
    """文本编辑器组件"""
    
    # 信号：文本变化
    text_changed = Signal()
    context_menu_requested = Signal()
    
    def __init__(self):
        super().__init__()
        self.setFont(QFont("Consolas", 10))
        self.setPlaceholderText("在此输入笔记内容...")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.textChanged.connect(lambda: self.text_changed.emit())
    
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
        find_action.triggered.connect(lambda: self.parent().parent().find_requested.emit())
        
        replace_action = menu.addAction("🔄 替换")
        replace_action.setShortcut(QKeySequence.Replace)
        replace_action.triggered.connect(lambda: self.parent().parent().replace_requested.emit())
        
        menu.addSeparator()
        
        # 保存
        save_action = menu.addAction("💾 保存")
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(lambda: self.parent().parent().save_requested.emit())
        
        menu.exec_(self.viewport().mapToGlobal(pos))
