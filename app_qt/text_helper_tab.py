"""
文本处理标签页 - PySide6 版本
迁移自 tabs/text_helper.py
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
                                QTextEdit, QListWidget, QPushButton, QLabel, 
                                QFrame, QGroupBox, QMenuBar)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QAction, QKeySequence
import pyperclip
import re
import os
import tempfile
import subprocess


class TextHelperTab(QWidget):
    """文本处理标签页"""
    
    def __init__(self, clipboard_callback=None):
        super().__init__()
        self.clipboard_callback = clipboard_callback
        self.clipboard_history = []
        self.max_clipboard_history = 50
        
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
        menubar = QMenuBar()
        main_layout.setMenuBar(menubar)
        
        # 创建文本处理菜单
        text_menu = menubar.addMenu("文本处理 (&T)")
        
        # 添加菜单项
        self.remove_newlines_action = QAction("去除换行符", self)
        self.remove_newlines_action.setShortcut(QKeySequence("Ctrl+Alt+L"))
        self.remove_newlines_action.triggered.connect(self.remove_newlines)
        text_menu.addAction(self.remove_newlines_action)
        
        self.double_newlines_action = QAction("添加双重换行符", self)
        self.double_newlines_action.setShortcut(QKeySequence("Ctrl+Alt+D"))
        self.double_newlines_action.triggered.connect(self.add_double_newlines)
        text_menu.addAction(self.double_newlines_action)
        
        self.remove_illegal_action = QAction("去除非法字符", self)
        self.remove_illegal_action.setShortcut(QKeySequence("Ctrl+Alt+I"))
        self.remove_illegal_action.triggered.connect(self.remove_illegal_chars)
        text_menu.addAction(self.remove_illegal_action)
        
        self.remove_filename_action = QAction("去除文件名非法字符", self)
        self.remove_filename_action.setShortcut(QKeySequence("Ctrl+Alt+F"))
        self.remove_filename_action.triggered.connect(self.remove_filename_illegal_chars)
        text_menu.addAction(self.remove_filename_action)
        
        self.markdown_to_docx_action = QAction("一键 markdown 渲染 docx", self)
        self.markdown_to_docx_action.setShortcut(QKeySequence("Ctrl+Alt+M"))
        self.markdown_to_docx_action.triggered.connect(self.convert_markdown_to_docx)
        text_menu.addAction(self.markdown_to_docx_action)
        
        text_menu.addSeparator()
        
        self.copy_action = QAction("复制结果", self)
        self.copy_action.setShortcut(QKeySequence("Ctrl+C"))
        self.copy_action.triggered.connect(self.copy_to_clipboard)
        text_menu.addAction(self.copy_action)
        
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
        result = content.replace('\n', '\n\n').replace('\r', '\r\r')
        self.text_input.setPlainText(result)
        
    def remove_newlines(self):
        """去除换行符"""
        content = self.text_input.toPlainText()
        result = content.replace('\n', ' ').replace('\r', ' ')
        self.text_input.setPlainText(result)
    
    def remove_illegal_chars(self):
        """去除非法字符"""
        content = self.text_input.toPlainText()
        result = ''.join(char for char in content if char.isprintable() or char in '\n\r\t ')
        result = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', result)
        self.text_input.setPlainText(result)
    
    def remove_filename_illegal_chars(self):
        """去除文件名非法字符"""
        content = self.text_input.toPlainText()
        allowed_chars = []
        for char in content:
            if char.isalnum():
                allowed_chars.append(char)
            elif char in '-_() ':
                allowed_chars.append(char)
            elif char.isspace():
                allowed_chars.append(' ')
        
        result = ''.join(allowed_chars)
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
            display_text = item[:50].replace('\n', '↵').replace('\r', '')
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
    
    def convert_markdown_to_docx(self):
        """将当前文本转换为 Word 文档"""
        content = self.text_input.toPlainText().strip()
        if not content:
            return
        
        try:
            # 创建临时 markdown 文件
            temp_dir = tempfile.gettempdir()
            temp_md = os.path.join(temp_dir, 'temp_document.md')
            temp_output_dir = os.path.join(temp_dir, 'docx_output')
            
            # 确保输出目录存在
            if not os.path.exists(temp_output_dir):
                os.makedirs(temp_output_dir)
            
            # 写入 markdown 文件
            with open(temp_md, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 构建 pandoc 命令
            cmd = [
                'pandoc',
                temp_md,
                '-o', os.path.join(temp_output_dir, 'document.docx'),
                "--reference-doc=custom_template.docx",
                '--extract-media=.'
            ]
            
            # 执行转换
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # 打开输出目录
            os.startfile(os.path.join(temp_output_dir, 'document.docx'))
            
        except subprocess.CalledProcessError as e:
            print(f"Pandoc 转换失败：{e}")
        except Exception as e:
            print(f"错误：{e}")
