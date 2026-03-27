from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from qtpy.QtCore import QTimer


class HighlightSlot:
    """语法高亮槽 - 带防抖机制"""
    
    DEBOUNCE_INTERVAL = 500  # 防抖间隔：500ms
    
    def __init__(self, widget):
        self._widget = widget
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._do_highlight)
        self._pending = False

    def widget(self):
        return self._widget

    def _getBackgroundColor(self):
        """获取当前主题背景色"""
        # 使用 SyntaxEdit 的方法获取与 QSS 一致的颜色
        return self.widget().getBackgroundColor()

    def execute(self):
        """触发高亮（带防抖）
        
        如果距离上次高亮不足 500ms，则延迟执行。
        这样可以避免输入时的频繁刷新导致的卡顿。
        """
        if self._timer.isActive():
            # 计时器正在运行，重置它
            self._timer.stop()
        
        # 启动计时器，延迟执行高亮
        self._timer.start(self.DEBOUNCE_INTERVAL)
        
        if not self._pending:
            self._pending = True
            print(f"[HighlightSlot] 高亮请求已延迟 {self.DEBOUNCE_INTERVAL}ms")

    def _do_highlight(self):
        """实际执行高亮渲染"""
        self._pending = False
        
        font = self.widget().editorFont()
        
        # 获取当前主题的背景色（与 QSS 一致）
        bg_color = self._getBackgroundColor()

        # 生成高亮 HTML
        highlighted = highlight(
            self.widget().toPlainText(),
            get_lexer_by_name(
                self.widget().syntax(),
                stripnl=False,
                ensurenl=False,
            ),
            HtmlFormatter(
                lineseparator="<br />",
                prestyles=f"white-space:pre-wrap; font-family: '{font}'; margin: 0; padding: 4px;",
                noclasses=True,
                nobackground=True,  # 不在 <pre> 上设置背景色
                style=self.widget().theme(),
            ),
        )

        # 包装在具有背景色的容器中，确保填满整个编辑器区域
        markup = f"""<!DOCTYPE html>
        <html>
        <head>
        <style>
            body, html {{
                margin: 0;
                padding: 0;
                background-color: {bg_color};
                min-height: 100%;
            }}
            .container {{
                background-color: {bg_color};
                min-height: 100%;
                padding: 0;
                margin: 0;
            }}
        </style>
        </head>
        <body>
            <div class="container">
                {highlighted}
            </div>
        </body>
        </html>"""

        position = self.widget().cursorPosition()

        self.widget().blockSignals(True)
        self.widget().setHtml(markup)
        self.widget().blockSignals(False)

        self.widget().setCursorPosition(position)
        
        print("[HighlightSlot] 高亮渲染完成")

    def flush(self):
        """立即执行高亮（不等待防抖）
        
        用于需要立即看到高亮结果的场景，如主题切换。
        """
        if self._timer.isActive():
            self._timer.stop()
        self._do_highlight()
