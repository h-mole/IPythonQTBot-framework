"""
自定义复选框组件
基于QLabel 实现，使用 Unicode 字符表示选中/未选中状态
提供类似于 QCheckBox 的 API
"""
from PySide6.QtWidgets import QLabel, QWidget, QHBoxLayout, QApplication, QVBoxLayout
from PySide6.QtCore import Signal, Qt, QEvent
from PySide6.QtGui import QFont, QCursor
from typing import Optional


class CustomCheckBox(QWidget):
    """
    自定义复选框组件
    
    使用 Unicode 字符来表示选中 (🗹) 或未选中 (☐) 状态
    提供类似于 QCheckBox 的 API 接口
    """
    
    # 状态改变信号
    stateChanged = Signal(int)  # int: 0=未选中，1=选中，2=部分选中
    toggled = Signal(bool)  # bool: 是否选中
    
    # Unicode 字符定义
    CHECKED_CHAR = "🗹"      # 选中状态
    UNCHECKED_CHAR = "☐"    # 未选中状态
    PARTIAL_CHAR = "▣"      # 部分选中状态（三态模式）
    
    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        """
        初始化自定义复选框
        
        Args:
            text: 复选框旁边的文本
            parent: 父组件
        """
        super().__init__(parent)
        
        self._text = text
        self._checked = False
        self._checkable = True
        self._autoExclusive = False
        self._tristate = False  # 三态模式
        
        # 设置布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 创建符号标签
        self.symbol_label = QLabel()
        self.symbol_label.setFont(QFont("Segoe UI Symbol", 14))
        self.symbol_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.update_symbol()
        
        # 创建文本标签
        self.text_label = QLabel(text)
        self.text_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # 添加到布局
        layout.addWidget(self.symbol_label)
        layout.addWidget(self.text_label)
        layout.addStretch()
        
        # 安装事件过滤器以支持点击
        self.symbol_label.installEventFilter(self)
        self.text_label.installEventFilter(self)
        
        # 设置样式
        self.setStyleSheet("""
            CustomCheckBox {
                background-color: transparent;
            }
            QLabel {
                color: #333333;
            }
        """)
    
    def update_symbol(self):
        """更新符号显示"""
        if self._tristate and not self._checked and hasattr(self, '_partial'):
            if self._partial:
                self.symbol_label.setText(self.PARTIAL_CHAR)
                return
        
        if self._checked:
            self.symbol_label.setText(self.CHECKED_CHAR)
        else:
            self.symbol_label.setText(self.UNCHECKED_CHAR)
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理点击事件"""
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent
        
        if event.type() == QEvent.Type.MouseButtonPress:
            if isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
                if self._checkable:
                    self.toggle()
                return True
        elif event.type() == QEvent.Type.Enter:
            # 鼠标悬停效果
            obj.setStyleSheet("color: #0078D4;")
        elif event.type() == QEvent.Type.Leave:
            # 恢复默认颜色
            obj.setStyleSheet("color: #333333;")
            
        return super().eventFilter(obj, event)
    
    def isChecked(self) -> bool:
        """
        检查是否选中
        
        Returns:
            bool: 是否选中
        """
        return self._checked
    
    def setChecked(self, checked: bool):
        """
        设置选中状态
        
        Args:
            checked: 是否选中
        """
        if self._checked != checked:
            self._checked = checked
            self.update_symbol()
            self.toggled.emit(checked)
            self.stateChanged.emit(1 if checked else 0)
    
    def toggle(self):
        """切换选中状态"""
        if self._tristate and hasattr(self, '_partial') and self._partial:
            # 三态模式下从部分选中切换到完全选中
            self._partial = False
            self.setChecked(True)
        else:
            self.setChecked(not self._checked)
    
    def checkState(self) -> Qt.CheckState:
        """
        获取选中状态（三态模式）
        
        Returns:
            Qt.CheckState: 选中状态
        """
        if self._tristate and hasattr(self, '_partial') and self._partial:
            return Qt.CheckState.PartiallyChecked
        return Qt.CheckState.Checked if self._checked else Qt.CheckState.Unchecked
    
    def setCheckState(self, state: Qt.CheckState):
        """
        设置选中状态（三态模式）
        
        Args:
            state: 选中状态
        """
        if self._tristate:
            if state == Qt.CheckState.PartiallyChecked:
                self._checked = False
                self._partial = True
                self.update_symbol()
                self.stateChanged.emit(2)
            else:
                self._partial = False
                self.setChecked(state == Qt.CheckState.Checked)
        else:
            self.setChecked(state == Qt.CheckState.Checked)
    
    def isCheckable(self) -> bool:
        """
        检查是否可勾选
        
        Returns:
            bool: 是否可勾选
        """
        return self._checkable
    
    def setCheckable(self, checkable: bool):
        """
        设置是否可勾选
        
        Args:
            checkable: 是否可勾选
        """
        self._checkable = checkable
    
    def setText(self, text: str):
        """
        设置复选框文本
        
        Args:
            text: 文本内容
        """
        self._text = text
        self.text_label.setText(text)
    
    def text(self) -> str:
        """
        获取复选框文本
        
        Returns:
            str: 文本内容
        """
        return self._text
    
    def isTristate(self) -> bool:
        """
        检查是否为三态模式
        
        Returns:
            bool: 是否为三态模式
        """
        return self._tristate
    
    def setTristate(self, tristate: bool = True):
        """
        设置三态模式
        
        Args:
            tristate: 是否启用三态模式
        """
        self._tristate = tristate
        if tristate and not hasattr(self, '_partial'):
            self._partial = False
    
    def setAutoExclusive(self, autoExclusive: bool):
        """
        设置自动互斥
        
        Args:
            autoExclusive: 是否自动互斥
        """
        self._autoExclusive = autoExclusive
        if autoExclusive:
            # 在同一父容器下的其他复选框取消选中
            parent_widget = self.parent()
            if parent_widget:
                for sibling in parent_widget.findChildren(CustomCheckBox):
                    if sibling is not self:
                        sibling.setChecked(False)
    
    def nextCheckState(self):
        """切换到下一个状态（供子类重写）"""
        self.toggle()


# 测试代码
if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    
    # 创建窗口
    window = QWidget()
    window.setWindowTitle("CustomCheckBox 测试")
    window.setGeometry(100, 100, 400, 300)
    
    layout = QVBoxLayout()
    
    # 基本用法
    cb1 = CustomCheckBox("基本复选框")
    cb2 = CustomCheckBox("可勾选复选框")
    cb2.setCheckable(True)
    cb2.setChecked(True)
    
    # 三态模式
    cb3 = CustomCheckBox("三态复选框")
    cb3.setTristate(True)
    cb3.setCheckState(Qt.CheckState.PartiallyChecked)
    
    # 信号连接
    def on_state_changed(state):
        print(f"状态改变：{state}")
    
    def on_toggled(checked):
        print(f"切换：{checked}")
    
    cb1.stateChanged.connect(on_state_changed)
    cb1.toggled.connect(on_toggled)
    
    layout.addWidget(cb1)
    layout.addWidget(cb2)
    layout.addWidget(cb3)
    layout.addStretch()
    
    window.setLayout(layout)
    window.show()
    
    sys.exit(app.exec())
