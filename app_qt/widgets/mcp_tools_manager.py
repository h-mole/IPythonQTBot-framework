"""
MCP 工具管理器组件 - 用于管理和配置 MCP 工具的启用/禁用状态
支持增量更新和延迟加载，每次显示时从 Agent 重新加载工具列表
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QScrollArea,
    QWidget,
    QLineEdit,
    QCompleter,
    QFrame,
    QHBoxLayout,
)
from PySide6.QtCore import Qt, Signal

from app_qt.plugin_manager import get_plugin_manager
from app_qt.widgets.custom_checkbox import CustomCheckBox
from app_qt.widgets.collapsible_group import CollapsibleGroup


class MCPToolsManagerWidget(QDialog):
    """MCP 工具管理器对话框组件"""
    
    tools_selection_changed = Signal(list, list)
    
    def __init__(self, parent=None, agent_instance=None):
        super().__init__(parent)
        self.setWindowTitle("MCP 工具管理")
        self.setMinimumSize(600, 500)
        
        self.agent_instance = agent_instance
        
        # 按命名空间分组的可折叠面板 {namespace: CollapsibleGroup}
        self.collapsible_groups: dict[str, CollapsibleGroup] = {}
        
        # 补全器模型
        self._completer_model = None
        
        self._init_base_ui()
    
    def _init_base_ui(self):
        """初始化基础 UI 框架"""
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(12)
        self.setLayout(self.main_layout)
        
        # 搜索框
        search_frame = QFrame()
        search_frame.setProperty("cssClass", "card")
        search_layout = QVBoxLayout(search_frame)
        search_layout.setContentsMargins(12, 8, 12, 8)
        
        search_label = QLabel("<b>搜索工具</b>")
        search_layout.addWidget(search_label)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入工具名称进行搜索...")
        
        self.completer = QCompleter(self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.search_edit.setCompleter(self.completer)
        self.search_edit.textChanged.connect(self._on_search_changed)
        
        search_layout.addWidget(self.search_edit)
        self.main_layout.addWidget(search_frame)
        
        # 工具列表区域
        tools_label = QLabel("<b>MCP 工具列表</b>")
        self.main_layout.addWidget(tools_label)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setProperty("cssClass", "card")
        
        self.scroll_content = QWidget()
        self.tools_layout = QVBoxLayout()
        self.tools_layout.setContentsMargins(8, 8, 8, 8)
        self.tools_layout.setSpacing(8)
        self.tools_layout.setAlignment(Qt.AlignTop)
        self.scroll_content.setLayout(self.tools_layout)
        self.scroll.setWidget(self.scroll_content)
        
        self.main_layout.addWidget(self.scroll, stretch=1)
        
        # 快捷操作按钮
        btn_frame = QFrame()
        btn_frame.setProperty("cssClass", "card")
        btn_layout = QVBoxLayout(btn_frame)
        btn_layout.setContentsMargins(12, 8, 12, 8)
        btn_layout.setSpacing(6)
        
        btn_label = QLabel("<b>快捷操作</b>")
        btn_layout.addWidget(btn_label)
        
        btn_row = QWidget()
        btn_row_layout = QHBoxLayout(btn_row)
        btn_row_layout.setContentsMargins(0, 0, 0, 0)
        btn_row_layout.setSpacing(8)
        
        # 全选所有 - 使用 btn-info 样式
        select_all_btn = QPushButton("全选所有")
        select_all_btn.setProperty("cssClass", "btn-info")
        select_all_btn.clicked.connect(lambda: self._set_all_checkboxes(True))
        btn_row_layout.addWidget(select_all_btn)
        
        # 反选所有 - 使用 btn-warning 样式
        invert_btn = QPushButton("反选所有")
        invert_btn.setProperty("cssClass", "btn-warning")
        invert_btn.clicked.connect(self._invert_all_checkboxes)
        btn_row_layout.addWidget(invert_btn)
        
        # 展开全部 - 使用 btn-secondary 样式
        expand_all_btn = QPushButton("展开全部")
        expand_all_btn.setProperty("cssClass", "btn-secondary")
        expand_all_btn.clicked.connect(self._expand_all_groups)
        btn_row_layout.addWidget(expand_all_btn)
        
        # 折叠全部 - 使用 btn-success 样式
        collapse_all_btn = QPushButton("折叠全部")
        collapse_all_btn.setProperty("cssClass", "btn-success")
        collapse_all_btn.clicked.connect(self._collapse_all_groups)
        btn_row_layout.addWidget(collapse_all_btn)
        
        btn_row_layout.addStretch()
        btn_layout.addWidget(btn_row)
        
        self.main_layout.addWidget(btn_frame)
        
        # 确定按钮 - 使用 btn-primary 样式
        ok_btn = QPushButton("确定")
        ok_btn.setProperty("cssClass", "btn-primary")
        ok_btn.clicked.connect(self._apply_selection)
        self.main_layout.addWidget(ok_btn)
    
    def refresh(self):
        """
        刷新工具列表（增量更新 + 延迟加载）
        
        从 Agent 重新加载工具列表，对比现有工具进行增量更新。
        复选框采用延迟创建策略，只有展开分组时才会创建。
        """
        # 获取最新的 MCP 工具列表
        pm = get_plugin_manager()
        all_methods = pm.get_all_methods(include_extra_data=True)
        mcp_tools = [m for m in all_methods if m.get('extra_data', {}).get('enable_mcp', False)]
        
        # 按命名空间分组
        namespace_groups: dict[str, list] = {}
        all_tool_names: list[str] = []
        
        for tool in mcp_tools:
            parts = tool['name'].split('.', 1)
            if len(parts) == 2:
                namespace = parts[0]
                method_name = parts[1]
                
                # 特殊处理 mcp_bridge 的格式
                if namespace == 'mcp_bridge' and '__' in method_name:
                    sub_group = method_name.split('__')[0]
                    group_key = f"{namespace}.{sub_group}"
                else:
                    group_key = namespace
                
                if group_key not in namespace_groups:
                    namespace_groups[group_key] = []
                namespace_groups[group_key].append(tool['name'])
                all_tool_names.append(tool['name'])
        
        # 更新补全器
        self._update_completer(all_tool_names)
        
        # 获取当前工具集合和新的工具集合
        current_groups = set(self.collapsible_groups.keys())
        new_groups = set(namespace_groups.keys())
        
        # 需要删除的分组
        groups_to_remove = current_groups - new_groups
        # 需要新增的分组
        groups_to_add = new_groups - current_groups
        
        # 删除不再存在的分组
        for group_key in groups_to_remove:
            self._remove_group(group_key)
        
        # 获取当前 Agent 的工具状态（用于新工具）
        default_checked = self._get_default_checked_state()
        
        # 更新或创建分组
        for group_key, tool_names in namespace_groups.items():
            if group_key in groups_to_add:
                # 创建新分组
                self._create_group(group_key, tool_names, default_checked)
            else:
                # 更新现有分组（增量更新工具）
                self._update_group_tools(group_key, tool_names, default_checked)
        
        print(f"[MCP 工具管理] 刷新完成：新增 {len(groups_to_add)} 个分组，"
              f"删除 {len(groups_to_remove)} 个分组，"
              f"当前共 {sum(len(tools) for tools in namespace_groups.values())} 个工具")
    
    def _get_default_checked_state(self) -> dict[str, bool]:
        """从 Agent 获取默认选中状态"""
        result = {}
        if not self.agent_instance:
            return result
        
        enabled_tools = set(self.agent_instance.mcp_tools_enabled)
        disabled_tools = set(self.agent_instance.mcp_tools_disabled)
        
        if not enabled_tools:
            # 全部启用模式：只有 disabled_tools 中的才被禁用
            for tool_name in disabled_tools:
                result[tool_name] = False
        else:
            # 白名单模式：只有 enabled_tools 中的才被启用
            for tool_name in enabled_tools:
                result[tool_name] = True
        
        return result
    
    def _update_completer(self, tool_names: list[str]):
        """更新补全器模型"""
        from PySide6.QtCore import QStringListModel
        self._completer_model = QStringListModel(sorted(tool_names), self)
        self.completer.setModel(self._completer_model)
    
    def _create_group(self, group_key: str, tool_names: list[str], default_checked: dict):
        """创建新分组"""
        group = CollapsibleGroup(group_key)
        group.set_select_all(True)
        group.toggled.connect(lambda expanded, g=group: self._on_group_toggled(g, expanded))
        
        # 添加工具（延迟创建）
        for tool_name in sorted(tool_names):
            checked = default_checked.get(tool_name, True if not default_checked else tool_name in default_checked)
            group.add_tool(tool_name, checked)
        
        self.collapsible_groups[group_key] = group
        self.tools_layout.addWidget(group)
    
    def _update_group_tools(self, group_key: str, new_tool_names: list[str], default_checked: dict):
        """增量更新分组中的工具"""
        group = self.collapsible_groups[group_key]
        
        # 获取当前工具
        current_tools = set(group._pending_tools.keys())
        new_tools = set(new_tool_names)
        
        # 需要删除的工具
        tools_to_remove = current_tools - new_tools
        # 需要新增的工具
        tools_to_add = new_tools - current_tools
        
        # 删除工具
        for tool_name in tools_to_remove:
            group.remove_tool(tool_name)
        
        # 添加新工具
        for tool_name in tools_to_add:
            checked = default_checked.get(tool_name, True if not default_checked else tool_name in default_checked)
            group.add_tool(tool_name, checked)
    
    def _remove_group(self, group_key: str):
        """移除分组"""
        if group_key not in self.collapsible_groups:
            return
        
        group = self.collapsible_groups[group_key]
        self.tools_layout.removeWidget(group)
        group.deleteLater()
        del self.collapsible_groups[group_key]
    
    def showEvent(self, event):
        """显示时自动刷新"""
        super().showEvent(event)
        self.refresh()
    
    def _on_search_changed(self, text: str):
        """搜索文本改变事件"""
        search_text = text.lower().strip()
        
        for group in self.collapsible_groups.values():
            if search_text:
                match_count = group.filter_tools(search_text)
                if match_count > 0:
                    group.expand()
            else:
                group.filter_tools("")
                group.collapse()
    
    def _on_group_toggled(self, group: CollapsibleGroup, expanded: bool):
        """组展开/折叠事件"""
        if expanded:
            search_text = self.search_edit.text().lower().strip()
            if search_text:
                group.filter_tools(search_text)
    
    def _set_all_checkboxes(self, state: bool):
        """设置所有复选框的状态"""
        for group in self.collapsible_groups.values():
            group.set_select_all(state)
    
    def _invert_all_checkboxes(self):
        """反选所有复选框"""
        for group in self.collapsible_groups.values():
            # 获取当前选中和未选中的工具
            checked = group.get_checked_tools()
            unchecked = group.get_unchecked_tools()
            
            # 交换状态
            for name in checked:
                group.set_tool_checked(name, False)
            for name in unchecked:
                group.set_tool_checked(name, True)
            
            group._update_select_all_state()
    
    def _expand_all_groups(self):
        """展开所有组"""
        for group in self.collapsible_groups.values():
            group.expand()
    
    def _collapse_all_groups(self):
        """折叠所有组"""
        for group in self.collapsible_groups.values():
            group.collapse()
    
    def _apply_selection(self):
        """应用 MCP 工具的选择状态"""
        enabled_tools = []
        disabled_tools = []
        
        for group in self.collapsible_groups.values():
            enabled_tools.extend(group.get_checked_tools())
            disabled_tools.extend(group.get_unchecked_tools())
        
        self.tools_selection_changed.emit(enabled_tools, disabled_tools)
        print(f"[MCP 工具管理] 已启用 {len(enabled_tools)} 个工具，禁用 {len(disabled_tools)} 个工具")
        self.accept()
    
    def get_selected_tools(self):
        """获取当前选择的工具"""
        enabled_tools = []
        disabled_tools = []
        
        for group in self.collapsible_groups.values():
            enabled_tools.extend(group.get_checked_tools())
            disabled_tools.extend(group.get_unchecked_tools())
        
        return enabled_tools, disabled_tools
