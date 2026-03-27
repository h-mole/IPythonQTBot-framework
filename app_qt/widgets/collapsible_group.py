"""
可折叠面板组件 - 支持延迟加载工具列表
用于 MCP 工具管理器等场景，支持展开/折叠内容区域
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QFrame,
)
from PySide6.QtCore import Qt, Signal

from app_qt.widgets.custom_checkbox import CustomCheckBox


class CollapsibleGroup(QWidget):
    """
    可折叠面板组件 - 支持延迟加载
    
    包含标题栏（名称 + 全选复选框 + 展开/折叠按钮）和内容区域
    默认状态为折叠，首次展开时才会创建复选框（延迟加载）
    """
    
    # 信号：展开状态改变时发射
    toggled = Signal(bool)
    # 信号：首次展开时发射，用于延迟加载
    first_expanded = Signal()
    
    def __init__(self, group_key: str, parent=None):
        """
        初始化可折叠面板
        
        Args:
            group_key: 分组键（命名空间）
            parent: 父组件
        """
        super().__init__(parent)
        
        self._group_key = group_key
        self._is_expanded = False
        self._is_content_created = False  # 标记内容是否已创建
        
        # 存储工具配置（延迟创建前）{tool_name: tool_info}
        self._pending_tools: dict = {}
        
        # 存储已创建的复选框 {tool_name: checkbox}
        self.tool_checkboxes: dict[str, CustomCheckBox] = {}
        
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 4, 0, 4)
        self.main_layout.setSpacing(0)
        
        # ===== 标题栏 =====
        self.header = QFrame()
        self.header.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(8)
        
        # 展开/折叠按钮
        self.toggle_btn = QToolButton()
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(False)
        self.toggle_btn.setArrowType(Qt.RightArrow)
        self.toggle_btn.setStyleSheet("""
            QToolButton {
                border: none;
                background: transparent;
                padding: 2px;
            }
            QToolButton:hover {
                background-color: #e0e0e0;
                border-radius: 3px;
            }
        """)
        self.toggle_btn.setFixedSize(20, 20)
        self.toggle_btn.clicked.connect(self._on_toggle_clicked)
        header_layout.addWidget(self.toggle_btn)
        
        # 标题标签
        self.title_label = QLabel(f"<b>{self._group_key}</b>")
        self.title_label.setStyleSheet("font-size: 11pt; color: #333;")
        header_layout.addWidget(self.title_label, stretch=1)
        
        # 工具计数标签
        self.count_label = QLabel("(0)")
        self.count_label.setStyleSheet("color: #666; font-size: 10pt;")
        header_layout.addWidget(self.count_label)
        
        # 全选复选框
        self.select_all_cb = CustomCheckBox("全选")
        self.select_all_cb.setChecked(True)
        self.select_all_cb.stateChanged.connect(self._on_select_all_changed)
        header_layout.addWidget(self.select_all_cb)
        
        self.main_layout.addWidget(self.header)
        
        # ===== 内容区域（初始为空）=====
        self.content_widget = QWidget()
        self.content_widget.setVisible(False)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(24, 4, 8, 4)
        self.content_layout.setSpacing(4)
        self.content_layout.setAlignment(Qt.AlignTop)
        
        self.main_layout.addWidget(self.content_widget)
        
        # 设置鼠标点击标题栏也可以展开/折叠
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.mousePressEvent = lambda e: self.toggle()
    
    def add_tool(self, tool_name: str, default_checked: bool = True):
        """
        添加工具到分组（延迟创建复选框）
        
        Args:
            tool_name: 工具名称
            default_checked: 默认是否选中
        """
        self._pending_tools[tool_name] = {"checked": default_checked}
        self._update_count_label()
    
    def _create_checkbox(self, tool_name: str, checked: bool) -> CustomCheckBox:
        """
        创建工具复选框
        
        Args:
            tool_name: 工具名称
            checked: 是否选中
        
        Returns:
            CustomCheckBox: 创建的复选框
        """
        cb = CustomCheckBox(f"  - {tool_name}")
        cb.setChecked(checked)
        cb.setProperty('tool_name', tool_name)
        cb.stateChanged.connect(self._update_select_all_state)
        return cb
    
    def _ensure_content_created(self):
        """确保内容已创建（延迟加载）"""
        if self._is_content_created:
            return
        
        # 批量创建复选框
        for tool_name, info in self._pending_tools.items():
            cb = self._create_checkbox(tool_name, info["checked"])
            self.tool_checkboxes[tool_name] = cb
            self.content_layout.addWidget(cb)
        
        self._is_content_created = True
        self.first_expanded.emit()
    
    def _on_toggle_clicked(self):
        """展开/折叠按钮点击事件"""
        self.toggle(self.toggle_btn.isChecked())
    
    def toggle(self, expand: bool = None):
        """
        切换展开/折叠状态
        
        Args:
            expand: 如果为 None，则切换当前状态；否则设置为指定状态
        """
        if expand is None:
            expand = not self._is_expanded
        
        self._is_expanded = expand
        self.toggle_btn.setChecked(expand)
        self.toggle_btn.setArrowType(Qt.DownArrow if expand else Qt.RightArrow)
        
        # 首次展开时创建内容
        if expand and not self._is_content_created:
            self._ensure_content_created()
        
        self.content_widget.setVisible(expand)
        self.toggled.emit(expand)
    
    def expand(self):
        """展开面板"""
        self.toggle(True)
    
    def collapse(self):
        """折叠面板"""
        self.toggle(False)
    
    def is_expanded(self) -> bool:
        """获取当前展开状态"""
        return self._is_expanded
    
    def set_tool_checked(self, tool_name: str, checked: bool):
        """
        设置工具的选中状态
        
        Args:
            tool_name: 工具名称
            checked: 是否选中
        """
        if tool_name in self.tool_checkboxes:
            self.tool_checkboxes[tool_name].setChecked(checked)
        elif tool_name in self._pending_tools:
            self._pending_tools[tool_name]["checked"] = checked
    
    def remove_tool(self, tool_name: str) -> bool:
        """
        移除工具
        
        Args:
            tool_name: 工具名称
        
        Returns:
            bool: 是否成功移除
        """
        removed = False
        
        # 从待处理列表中移除
        if tool_name in self._pending_tools:
            del self._pending_tools[tool_name]
            removed = True
        
        # 从已创建复选框中移除
        if tool_name in self.tool_checkboxes:
            cb = self.tool_checkboxes[tool_name]
            self.content_layout.removeWidget(cb)
            cb.deleteLater()
            del self.tool_checkboxes[tool_name]
            removed = True
        
        if removed:
            self._update_count_label()
            self._update_select_all_state()
        
        return removed
    
    def get_tool_count(self) -> int:
        """获取工具总数"""
        return len(self._pending_tools)
    
    def has_tools(self) -> bool:
        """检查是否还有工具"""
        return len(self._pending_tools) > 0
    
    def _update_count_label(self):
        """更新工具计数标签"""
        total = len(self._pending_tools)
        enabled = sum(
            1 for info in self._pending_tools.values()
            if info.get("checked", True)
        )
        self.count_label.setText(f"({enabled}/{total})")
    
    def _update_select_all_state(self):
        """根据子复选框状态更新全选复选框状态"""
        if not self.tool_checkboxes:
            return
        
        checked_count = sum(1 for cb in self.tool_checkboxes.values() if cb.isChecked())
        total = len(self.tool_checkboxes)
        
        self.select_all_cb.blockSignals(True)
        if checked_count == 0:
            self.select_all_cb.setChecked(False)
        elif checked_count == total:
            self.select_all_cb.setChecked(True)
        self.select_all_cb.blockSignals(False)
        
        self._update_count_label()
    
    def _on_select_all_changed(self, state):
        """全选复选框状态改变事件"""
        checked = (state == True or state == 1)
        
        # 更新待处理工具的状态
        for info in self._pending_tools.values():
            info["checked"] = checked
        
        # 更新已创建复选框的状态
        for cb in self.tool_checkboxes.values():
            cb.setChecked(checked)
        
        self._update_count_label()
    
    def set_select_all(self, checked: bool):
        """设置全选状态"""
        self.select_all_cb.blockSignals(True)
        self.select_all_cb.setChecked(checked)
        self.select_all_cb.blockSignals(False)
        
        # 更新所有工具状态
        for info in self._pending_tools.values():
            info["checked"] = checked
        for cb in self.tool_checkboxes.values():
            cb.setChecked(checked)
        
        self._update_count_label()
    
    def get_checked_tools(self) -> list[str]:
        """获取当前选中的工具名称列表"""
        result = []
        # 已创建的复选框
        for name, cb in self.tool_checkboxes.items():
            if cb.isChecked():
                result.append(name)
        # 待处理列表中的工具
        for name, info in self._pending_tools.items():
            if name not in self.tool_checkboxes and info.get("checked", True):
                result.append(name)
        return result
    
    def get_unchecked_tools(self) -> list[str]:
        """获取当前未选中的工具名称列表"""
        result = []
        # 已创建的复选框
        for name, cb in self.tool_checkboxes.items():
            if not cb.isChecked():
                result.append(name)
        # 待处理列表中的工具
        for name, info in self._pending_tools.items():
            if name not in self.tool_checkboxes and not info.get("checked", True):
                result.append(name)
        return result
    
    def filter_tools(self, search_text: str) -> int:
        """
        根据搜索文本过滤显示工具
        
        Args:
            search_text: 搜索文本（小写）
        
        Returns:
            int: 匹配的工具数量
        """
        if not self._is_content_created:
            # 未展开时，只在待处理列表中计数
            return sum(1 for name in self._pending_tools if search_text in name.lower())
        
        match_count = 0
        for tool_name, cb in self.tool_checkboxes.items():
            match = search_text in tool_name.lower()
            cb.setVisible(match)
            if match:
                match_count += 1
        return match_count
    
    def block_checkbox_signals(self, block: bool):
        """阻塞/恢复所有复选框的信号"""
        for cb in self.tool_checkboxes.values():
            cb.blockSignals(block)
