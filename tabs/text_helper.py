import tkinter as tk
from tkinter import ttk, scrolledtext
import pyperclip
import re


class TextHelperTab:
    """文本处理标签页"""
    
    def __init__(self, parent, clipboard_callback=None):
        self.parent = parent
        self.clipboard_callback = clipboard_callback  # 用于回调添加剪贴板历史
        
        # 使用 PanedWindow 实现左右分栏
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：文本处理区域
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        # 输入文本框（原位替换）
        input_frame = ttk.LabelFrame(left_frame, text="输入文本", padding=5)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text_input = scrolledtext.ScrolledText(input_frame, height=15, font=("Consolas", 10))
        self.text_input.pack(fill=tk.BOTH, expand=True)
        
        # 按钮区域
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(pady=10, padx=5)
        
        # 核心功能按钮：去除换行
        action_btn = ttk.Button(
            btn_frame, 
            text="一键去除换行符", 
            command=self.remove_newlines,
            width=18
        )
        action_btn.pack(side=tk.LEFT, padx=5)
        
        # 去除非法字符
        clean_btn = ttk.Button(
            btn_frame,
            text="一键去除非法字符",
            command=self.remove_illegal_chars,
            width=18
        )
        clean_btn.pack(side=tk.LEFT, padx=5)
        
        # 去除文件名非法字符
        filename_btn = ttk.Button(
            btn_frame,
            text="去除文件名非法字符",
            command=self.remove_filename_illegal_chars,
            width=20
        )
        filename_btn.pack(side=tk.LEFT, padx=5)
        
        # 辅助按钮：复制结果
        copy_btn = ttk.Button(
            btn_frame, 
            text="复制结果", 
            command=self.copy_to_clipboard,
            width=15
        )
        copy_btn.pack(side=tk.LEFT, padx=5)
        
        # 右侧：剪贴板历史
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=0)
        
        clipboard_frame = ttk.LabelFrame(right_frame, text="📋 剪贴板历史", padding=5)
        clipboard_frame.pack(fill=tk.BOTH, expand=True)
        
        # 剪贴板历史列表
        self.clipboard_list = tk.Listbox(clipboard_frame, font=("Consolas", 9), selectmode=tk.SINGLE)
        self.clipboard_list.pack(fill=tk.BOTH, expand=True)
        
        # 双击事件绑定
        self.clipboard_list.bind('<Double-Button-1>', self.load_clipboard_item)
        
        # 清空按钮
        clear_btn = ttk.Button(
            clipboard_frame,
            text="清空历史",
            command=self.clear_clipboard_history
        )
        clear_btn.pack(pady=5)
        
        # 剪贴板历史记录
        self.clipboard_history = []
        self.max_clipboard_history = 50
        
        # 初始化时加载一次剪贴板内容
        try:
            initial_content = pyperclip.paste() if pyperclip else self.parent.clipboard_get()
            if initial_content:
                self.add_to_clipboard_history(initial_content)
        except:
            pass
    
    def remove_newlines(self):
        """核心逻辑：去除换行符（原位替换）"""
        content = self.text_input.get("1.0", tk.END)
        
        # 去除所有换行符 (\n, \r, \r\n)
        result = content.replace('\n', '').replace('\r', '')
        
        # 原位替换：先删除全部内容，再插入新内容
        self.text_input.delete("1.0", tk.END)
        self.text_input.insert("1.0", result)
    
    def remove_illegal_chars(self):
        """去除非法字符（原位替换）"""
        content = self.text_input.get("1.0", tk.END)
        
        # 定义非法字符：不可打印字符（除了常见的空白字符）
        # 保留：空格、制表符、换行符等
        # 移除：控制字符和其他非法字符
        result = ''.join(char for char in content if char.isprintable() or char in '\n\r\t ')
        
        # 额外去除一些常见的非法 Unicode 字符
        result = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', result)
        
        # 原位替换
        self.text_input.delete("1.0", tk.END)
        self.text_input.insert("1.0", result)
    
    def remove_filename_illegal_chars(self):
        """去除文件名非法字符（原位替换）"""
        content = self.text_input.get("1.0", tk.END)
        
        # 只保留字母、数字、汉字、-_() 和空格
        # 去除所有其他字符
        allowed_chars = []
        for char in content:
            # 保留字母、数字、汉字
            if char.isalnum():
                allowed_chars.append(char)
            # 保留特定符号：- _ ( )
            elif char in '-_() ':
                allowed_chars.append(char)
            # 保留空格
            elif char.isspace():
                allowed_chars.append(' ')
        
        result = ''.join(allowed_chars)
        
        # 原位替换
        self.text_input.delete("1.0", tk.END)
        self.text_input.insert("1.0", result)
    
    def copy_to_clipboard(self, text=None):
        """复制内容到剪贴板"""
        if text is None:
            text = self.text_input.get("1.0", tk.END).strip()
        
        if not text:
            return

        try:
            # 尝试使用 pyperclip (如果安装了)
            pyperclip.copy(text)
        except ImportError:
            # 回退到 tkinter 自带剪贴板
            self.parent.clipboard_clear()
            self.parent.clipboard_append(text)
            self.parent.update()  # 必须更新事件队列才能生效
    
    def add_to_clipboard_history(self, text):
        """添加文本到剪贴板历史"""
        if not text or text.strip() == "":
            return
        
        # 避免重复添加
        if text in self.clipboard_history:
            self.clipboard_history.remove(text)
        
        # 添加到列表开头
        self.clipboard_history.insert(0, text)
        
        # 限制历史记录数量
        if len(self.clipboard_history) > self.max_clipboard_history:
            self.clipboard_history.pop()
        
        # 更新列表框显示
        self.update_clipboard_list()
        
        # 如果有回调函数，调用它
        if self.clipboard_callback:
            self.clipboard_callback(text)
    
    def update_clipboard_list(self):
        """更新剪贴板历史列表显示"""
        self.clipboard_list.delete(0, tk.END)
        
        for i, item in enumerate(self.clipboard_history):
            # 显示前 50 个字符
            display_text = item[:50].replace('\n', '↵').replace('\r', '')
            if len(item) > 50:
                display_text += "..."
            self.clipboard_list.insert(tk.END, f"[{i+1}] {display_text}")
    
    def load_clipboard_item(self, event=None):
        """双击加载剪贴板历史项到文本处理框"""
        selection = self.clipboard_list.curselection()
        if not selection:
            return
        
        index = selection[0]
        if 0 <= index < len(self.clipboard_history):
            item = self.clipboard_history[index]
            # 加载到文本处理框
            self.text_input.delete("1.0", tk.END)
            self.text_input.insert("1.0", item)
    
    def clear_clipboard_history(self):
        """清空剪贴板历史"""
        self.clipboard_history.clear()
        self.update_clipboard_list()
    
    def monitor_clipboard(self):
        """后台监控剪贴板变化"""
        last_clipboard = ""
        
        def check_clipboard():
            nonlocal last_clipboard
            try:
                current = pyperclip.paste() if pyperclip else self.parent.clipboard_get()
                if current and current != last_clipboard:
                    last_clipboard = current
                    self.add_to_clipboard_history(current)
            except:
                pass
            # 每 1 秒检查一次
            self.parent.after(1000, check_clipboard)
        
        check_clipboard()