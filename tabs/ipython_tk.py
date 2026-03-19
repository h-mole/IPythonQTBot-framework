"""
IPython Tkinter Frontend
需要安装：pip install ipython tk
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import sys
from io import StringIO


class IPythonTkFrontend:
    """IPython Tkinter 前端界面"""
    
    def __init__(self, parent):
        self.parent = parent
        
        # 创建主框架
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 标题
        title_label = ttk.Label(
            main_frame, 
            text="🐍 IPython 交互式控制台", 
            font=("Microsoft YaHei UI", 12, "bold")
        )
        title_label.pack(pady=5)
        
        # 输出区域（只读）
        output_frame = ttk.LabelFrame(main_frame, text="输出", padding=5)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=10, font=("Consolas", 10), state='disabled')
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # 输入区域
        input_frame = ttk.LabelFrame(main_frame, text="输入 (按 Enter 执行)", padding=5)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.input_entry = ttk.Entry(input_frame, font=("Consolas", 10))
        self.input_entry.pack(fill=tk.X, padx=5, pady=5)
        self.input_entry.bind('<Return>', self.execute_command)
        
        # 按钮区域
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(pady=5)
        
        exec_btn = ttk.Button(
            btn_frame,
            text="执行",
            command=self.execute_command
        )
        exec_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = ttk.Button(
            btn_frame,
            text="清空输出",
            command=self.clear_output
        )
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # IPython 相关
        self.ipython = None
        self.output_buffer = StringIO()
        
        # 在后台线程中初始化 IPython
        self.init_ipython()
    
    def init_ipython(self):
        """初始化 IPython"""
        def init():
            try:
                from IPython.terminal.interactiveshell import TerminalInteractiveShell
                
                # 创建 IPython 实例
                self.ipython = TerminalInteractiveShell.instance()
                
                # 重定向标准输出和错误输出到我们的缓冲区
                import sys
                sys.stdout = self.output_buffer
                sys.stderr = self.output_buffer
                
                self.append_output("IPython 初始化成功！\n")
                self.append_output("提示：使用 exit() 退出，使用 ? 获取帮助\n\n")
            except ImportError as e:
                self.append_output(f"错误：未安装 IPython\n")
                self.append_output(f"请运行：pip install ipython\n")
                self.append_output(f"详细信息：{e}\n\n")
            except Exception as e:
                self.append_output(f"IPython 初始化失败：{e}\n")
                self.append_output(f"错误类型：{type(e).__name__}\n\n")
        
        # 在后台线程中初始化
        thread = threading.Thread(target=init, daemon=True)
        thread.start()
    
    def execute_command(self, event=None):
        """执行命令"""
        command = self.input_entry.get().strip()
        if not command:
            return
        
        # 清空输入框
        self.input_entry.delete(0, tk.END)
        
        # 显示输入的命令
        self.append_output(f">>> {command}\n")
        
        # 执行命令
        def run():
            try:
                if self.ipython:
                    # 清空缓冲区
                    self.output_buffer.truncate(0)
                    self.output_buffer.seek(0)
                    
                    # 执行并获取完整输出（包括错误）
                    result = self.ipython.run_cell(
                        command,
                        store_history=False,
                        silent=False,
                        shell_futures=True
                    )
                    
                    # 获取所有输出（stdout 和 stderr）
                    output = self.output_buffer.getvalue()
                    
                    # 如果有执行结果（不是 None），也显示
                    if result.result is not None and result.success:
                        output += f"Out: {result.result}\n"
                    
                    # 如果执行失败，显示错误信息
                    if not result.success:
                        if result.error_in_exec:
                            import traceback
                            output += "\n"
                            if hasattr(result.error_in_exec, '__traceback__'):
                                output += ''.join(traceback.format_exception(type(result.error_in_exec), result.error_in_exec, result.error_in_exec.__traceback__))
                            else:
                                output += f"错误：{result.error_in_exec}\n"
                    
                    # 更新到 GUI
                    if output:
                        self.append_output(output)
                    else:
                        self.append_output("\n")
            except Exception as e:
                self.append_output(f"执行错误：{e}\n")
                import traceback
                self.append_output(traceback.format_exc())
                self.append_output("\n")
        
        # 在后台线程中执行
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
    
    def append_output(self, text):
        """添加输出文本"""
        def update():
            self.output_text.config(state='normal')
            self.output_text.insert(tk.END, text)
            self.output_text.see(tk.END)  # 滚动到底部
            self.output_text.config(state='disabled')
        
        self.parent.after(0, update)
    
    def clear_output(self):
        """清空输出"""
        self.output_text.config(state='normal')
        self.output_text.delete("1.0", tk.END)
        self.output_text.config(state='disabled')


# 测试函数
def test():
    """测试运行"""
    root = tk.Tk()
    root.title("IPython Tkinter Frontend")
    root.geometry("800x600")
    
    app = IPythonTkFrontend(root)
    root.mainloop()


if __name__ == "__main__":
    test()