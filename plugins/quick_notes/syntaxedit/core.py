from qtpy import QtGui
from qtpy.QtWidgets import QTextEdit, QPlainTextEdit, QApplication
from qtpy.QtCore import QEvent, QTimer

from pygments.styles import get_style_by_name


from .highlightslot import HighlightSlot

# 主题颜色定义（与 QSS 保持一致）
THEME_COLORS = {
    "light": {
        "bg": "#ffffff",
        "text": "#1f2937",
    },
    "dark": {
        "bg": "#262626",
        "text": "#f5f5f5",
    },
}


class SyntaxEdit(QTextEdit):
    def __init__(
        self,
        content="",
        parent=None,
        font="Courier New",
        font_size=13,
        syntax="Markdown",
        theme="default",
        indentation_size=4,
        use_theme_background=False,
    ):
        super().__init__("", parent)

        self._indentation_size = indentation_size

        self._font = font
        self._font_size = font_size
        self._setFontValues()

        self._syntax = syntax
        self._theme = theme
        self._pygments_theme_light = "default"
        self._pygments_theme_dark = "monokai"

        self._use_theme_background = use_theme_background

        # 设置 viewport 边距为 0，防止出现亮色边框
        self.setViewportMargins(0, 0, 0, 0)
        # 设置文档边距为 0
        self.document().setDocumentMargin(0)

        self._highlight_slot = HighlightSlot(self)
        self.textChanged.connect(self._highlight_slot.execute)
        
        self.setPlainText(content)
        
        # 延迟检测主题并立即高亮（首次不等待防抖）
        self._initialHighlight()

    def _initialHighlight(self):
        """初始化时立即高亮（不等待防抖）"""
        # 先根据当前主题设置 Pygments 主题
        detected_theme = self._detectThemeFromBackground()
        self._theme = (
            self._pygments_theme_dark if detected_theme == "dark" else self._pygments_theme_light
        )
        # 立即高亮，不等待防抖定时器
        self._highlight_slot.flush()
        print(f"[SyntaxEdit] 初始化高亮完成，主题: {self._theme}")

    def _getCurrentTheme(self):
        """获取当前应用主题"""
        try:
            from app_qt.widgets.theme_manager import get_theme_manager
            return get_theme_manager().get_current_theme()
        except:
            return "light"

    def _getThemeColor(self, color_type="bg"):
        """获取当前主题的颜色"""
        theme = self._getCurrentTheme()
        return THEME_COLORS.get(theme, THEME_COLORS["light"]).get(color_type, "#ffffff")

    def _setFontValues(self):
        self.setFont(QtGui.QFont(self._font, self._font_size))
        self.setTabStopDistance(
            QtGui.QFontMetricsF(self.font()).horizontalAdvance(" ") * 4
        )

    def _detectThemeFromBackground(self):
        """根据当前主题管理器检测主题"""
        return self._getCurrentTheme()

    def _updatePygmentsTheme(self):
        """根据检测到的主题更新 Pygments 语法高亮主题"""
        detected_theme = self._detectThemeFromBackground()
        new_pygments_theme = (
            self._pygments_theme_dark if detected_theme == "dark" else self._pygments_theme_light
        )
        if new_pygments_theme != self._theme:
            self._theme = new_pygments_theme
            # 主题切换时立即刷新，不等待防抖
            self._highlight_slot.flush()
            print(f"[SyntaxEdit] 自动切换语法高亮主题: {self._theme}")

    def setSyntax(self, syntax: str):
        self._syntax = syntax
        self.textChanged.emit()

    def syntax(self):
        return self._syntax

    def theme(self):
        return self._theme

    def setTheme(self, theme):
        """设置语法高亮主题
        
        注意：这控制的是 Pygments 语法高亮颜色，而非编辑器背景色。
        背景色由应用 QSS 主题控制。
        """
        self._theme = theme
        self.textChanged.emit()

    def setPygmentsThemes(self, light_theme: str, dark_theme: str):
        """设置浅色和深色模式对应的 Pygments 主题
        
        Args:
            light_theme: 浅色模式使用的 Pygments 主题名（如 "default"）
            dark_theme: 深色模式使用的 Pygments 主题名（如 "monokai"）
        """
        self._pygments_theme_light = light_theme
        self._pygments_theme_dark = dark_theme
        self._updatePygmentsTheme()

    def indentationSize(self):
        return self._indentation_size

    def editorFont(self):
        return self.currentFont().family()

    def editorFontSize(self):
        return self.currentFont().pointSize()

    def setEditorFontSize(self, size):
        self._font_size = size
        self._setFontValues()

    def cursorPosition(self):
        return self.textCursor().position()

    def setCursorPosition(self, position):
        cursor = self.textCursor()
        cursor.setPosition(position)
        self.setTextCursor(cursor)

    def setContents(self, contents):
        self.setPlainText(contents)

    def getBackgroundColor(self):
        """获取当前主题背景色（供 HighlightSlot 使用）"""
        return self._getThemeColor("bg")

    def setAppTheme(self, app_theme: str):
        """手动设置应用主题并更新语法高亮主题
        
        Args:
            app_theme: "light" 或 "dark"
        """
        if app_theme == "dark":
            self._theme = self._pygments_theme_dark
        else:
            self._theme = self._pygments_theme_light
        self.textChanged.emit()
        print(f"[SyntaxEdit] 手动切换语法高亮主题: {self._theme}")
