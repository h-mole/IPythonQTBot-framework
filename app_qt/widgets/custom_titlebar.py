"""
自定义标题栏组件 - 无边框窗口设计
"""

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QToolButton,
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QFont, QCursor


class CustomTitleBar(QWidget):
    """自定义标题栏组件"""

    # 信号
    minimize_clicked = Signal()
    maximize_clicked = Signal()
    restore_clicked = Signal()
    close_clicked = Signal()

    def __init__(self, parent=None, title: str = "IPythonQTBot", icon: str = "🛠️", show_subtitle: bool = False, subtitle: str = ""):
        super().__init__(parent)
        self.parent_window = parent
        self.title_text = title
        self.icon_text = icon
        self.show_subtitle = show_subtitle
        self.subtitle_text = subtitle
        
        # 拖动相关
        self.dragging = False
        self.drag_start_pos = QPoint()
        
        self.init_ui()
        
    def init_ui(self):
        """初始化 UI"""
        self.setObjectName("titleBarWidget")
        self.setFixedHeight(48)
        
        # 主布局
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # ========== 左侧：图标和标题 ==========
        left_layout = QHBoxLayout()
        left_layout.setSpacing(8)
        
        # 应用图标
        self.icon_label = QLabel(self.icon_text)
        self.icon_label.setObjectName("appIconLabel")
        left_layout.addWidget(self.icon_label)
        
        # 应用标题
        self.title_label = QLabel(self.title_text)
        self.title_label.setObjectName("appTitleLabel")
        # 设置深色标题文字
        self.title_label.setStyleSheet("font-size: 13pt; font-weight: bold; color: #2c3e50;")
        if self.show_subtitle and self.subtitle_text:
            # 如果显示副标题，使用垂直布局
            title_layout = QVBoxLayout()
            title_layout.setSpacing(2)
            title_layout.setContentsMargins(0, 0, 0, 0)
            
            self.title_label = QLabel(self.title_text)
            self.title_label.setObjectName("appTitleLabel")
            self.title_label.setStyleSheet("font-size: 13pt; font-weight: bold; color: white;")
            
            self.subtitle_label = QLabel(self.subtitle_text)
            self.subtitle_label.setObjectName("appSubtitleLabel")
            self.subtitle_label.setStyleSheet("font-size: 9pt; color: #bdc3c7;")
            
            title_layout.addWidget(self.title_label)
            title_layout.addWidget(self.subtitle_label)
            
            left_layout.addLayout(title_layout)
        else:
            left_layout.addWidget(self.title_label)
        
        main_layout.addLayout(left_layout)
        
        main_layout.addStretch()
        
        # ========== 右侧：窗口控制按钮 ==========
        right_layout = QHBoxLayout()
        right_layout.setSpacing(0)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 最小化按钮
        self.minimize_btn = QToolButton()
        self.minimize_btn.setObjectName("titleBarButton")
        self.minimize_btn.setText("─")  # Unicode 减号
        self.minimize_btn.setToolTip("最小化")
        self.minimize_btn.setFixedSize(46, 48)
        self.minimize_btn.clicked.connect(self.on_minimize_clicked)
        
        right_layout.addWidget(self.minimize_btn)
        
        # 最大化/还原按钮
        self.maximize_btn = QToolButton()
        self.maximize_btn.setObjectName("titleBarButton")
        self.maximize_btn.setText("◻")  # Unicode 方块
        self.maximize_btn.setToolTip("最大化")
        self.maximize_btn.setFixedSize(46, 48)
        self.maximize_btn.clicked.connect(self.on_maximize_clicked)
        # 设置深色按钮符号
        right_layout.addWidget(self.maximize_btn)
        
        # 关闭按钮
        self.close_btn = QToolButton()
        self.close_btn.setObjectName("titleBarButton")
        self.close_btn.setText("✕")  # Unicode 乘号
        self.close_btn.setToolTip("关闭")
        self.close_btn.setFixedSize(46, 48)
        self.close_btn.clicked.connect(self.on_close_clicked)
        right_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(right_layout)
    
    def on_minimize_clicked(self):
        """最小化按钮点击事件"""
        if self.parent_window:
            self.parent_window.showMinimized()
        self.minimize_clicked.emit()
    
    def on_maximize_clicked(self):
        """最大化按钮点击事件"""
        if self.parent_window:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
                self.maximize_btn.setText("□")
                self.maximize_btn.setToolTip("最大化")
            else:
                self.parent_window.showMaximized()
                self.maximize_btn.setText("❐")  # Unicode 重叠方块
                self.maximize_btn.setToolTip("还原")
        self.maximize_btn.style().unpolish(self.maximize_btn)
        self.maximize_btn.style().polish(self.maximize_btn)
    
    def on_close_clicked(self):
        """关闭按钮点击事件"""
        if self.parent_window:
            self.parent_window.close()
        self.close_clicked.emit()
    
    def update_title(self, title: str):
        """更新标题"""
        self.title_text = title
        self.title_label.setText(title)
    
    def update_icon(self, icon: str):
        """更新图标"""
        self.icon_text = icon
        self.icon_label.setText(icon)
    
    def mouseDoubleClickEvent(self, event):
        """双击标题栏切换最大化"""
        if event.button() == Qt.LeftButton:
            self.on_maximize_clicked()
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 开始拖动"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_pos = event.globalPos()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖动窗口"""
        if self.dragging and self.parent_window:
            # 计算移动距离
            delta = event.globalPos() - self.drag_start_pos
            # 移动窗口
            self.parent_window.move(self.parent_window.pos() + delta)
            # 更新起始位置
            self.drag_start_pos = event.globalPos()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件 - 结束拖动"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
