import os
# 【关键修改】强制使用软件渲染，解决白屏问题
# 必须在导入 PySide6 和创建 QApplication 之前设置
os.environ['QT_OPENGL'] = 'software'
# 某些情况下还需要这个变量来禁用 Chromium 的 GPU 加速

os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--disable-gpu'
from PySide6.QtCore import QObject, QTimer, Signal, Slot


from QMarkdownView import MarkdownView, LinkMiddlewarePolicy, QApplication

app  = QApplication()
widget = MarkdownView()
widget.setExtensions(["markdown.extensions.tables", "markdown.extensions.extra"])

widget.setValue("# Hello world!")
widget.loadFinished.connect(lambda: widget.setValue("# Hello world!"))
widget.show()

app.exec()
