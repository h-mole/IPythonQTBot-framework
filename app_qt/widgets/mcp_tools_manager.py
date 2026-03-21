"""
MCP 工具管理器组件 - 用于管理和配置 MCP 工具的启用/禁用状态
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QCheckBox,
    QPushButton,
    QLabel,
    QScrollArea,
    QWidget,
)
from PySide6.QtCore import Qt, Signal
from app_qt.plugin_manager import get_plugin_manager


class MCPToolsManagerWidget(QDialog):
    """MCP 工具管理器对话框组件"""
    
    # 信号：当用户确认选择后发射，传递启用和禁用的工具名称列表
    tools_selection_changed = Signal(list, list)
    
    def __init__(self, parent=None, agent_instance=None):
        """
        初始化 MCP 工具管理器
        
        Args:
            parent: 父窗口
            agent_instance: Agent 实例（用于获取当前的工具过滤状态）
        """
        super().__init__(parent)
        self.setWindowTitle("MCP 工具管理")
        self.setMinimumSize(500, 400)
        
        self.agent_instance = agent_instance
        self.method_checkboxes = {}
        
        self._init_ui()
        self._load_tools_from_agent()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 获取插件管理器
        pm = get_plugin_manager()
        
        # 获取所有 MCP 工具
        all_methods = pm.get_all_methods(include_extra_data=True)
        mcp_tools = [m for m in all_methods if m.get('extra_data', {}).get('enable_mcp', False)]
        
        # 按命名空间分组（支持 mcp_bridge 的特殊格式）
        namespace_groups = {}
        for tool in mcp_tools:
            parts = tool['name'].split('.', 1)
            if len(parts) == 2:
                namespace = parts[0]
                method_name = parts[1]
                
                # 特殊处理 mcp_bridge 的格式：mcp_bridge.mcd-mcp__xxxx
                # 需要按照双下划线前面的部分作为子分组
                if namespace == 'mcp_bridge' and '__' in method_name:
                    sub_group = method_name.split('__')[0]  # 例如：mcd-mcp
                    group_key = f"{namespace}.{sub_group}"
                else:
                    group_key = namespace
                
                if group_key not in namespace_groups:
                    namespace_groups[group_key] = []
                namespace_groups[group_key].append(tool)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        content_layout = QVBoxLayout()
        scroll_content.setLayout(content_layout)
        scroll.setWidget(scroll_content)
        
        # 存储复选框的字典
        namespace_checkboxes = {}
        self.method_checkboxes = {}
        
        # 为每个分组创建组
        for group_key, tools in sorted(namespace_groups.items()):
            # 分组标题
            ns_label = QLabel(f"<b>{group_key}</b>")
            ns_label.setStyleSheet("font-size: 12pt; margin-top: 8px;")
            content_layout.addWidget(ns_label)
            
            # 分组全选复选框
            ns_checkbox = QCheckBox(f"全选/全不选 {group_key}")
            ns_checkbox.setChecked(True)  # 默认全选，后续会根据 agent 状态调整
            content_layout.addWidget(ns_checkbox)
            
            # 存储分组的复选框引用
            namespace_checkboxes[group_key] = ns_checkbox
            self.method_checkboxes[group_key] = []
            
            # 该分组下的所有方法
            for tool in tools:
                method_cb = QCheckBox(f"  - {tool['name']}")
                method_cb.setChecked(True)  # 默认启用，后续会根据 agent 状态调整
                method_cb.setProperty('tool_name', tool['name'])
                content_layout.addWidget(method_cb)
                self.method_checkboxes[group_key].append(method_cb)
            
            # 绑定分组复选框的联动事件
            def on_ns_toggle(state, group=group_key):
                """分组全选/全不选切换"""
                for cb in self.method_checkboxes[group]:
                    cb.setChecked(state == Qt.CheckState.Checked)
            
            ns_checkbox.stateChanged.connect(on_ns_toggle)
            
            # 添加分隔线
            separator = QLabel()
            separator.setStyleSheet("background-color: #ddd; height: 1px; margin: 4px 0;")
            content_layout.addWidget(separator)
        
        # 全选和反选按钮
        btn_layout = QVBoxLayout()
        
        select_all_btn = QPushButton("✅ 全选所有")
        select_all_btn.clicked.connect(lambda: self._set_all_checkboxes(True))
        btn_layout.addWidget(select_all_btn)
        
        invert_btn = QPushButton("🔄 反选所有")
        invert_btn.clicked.connect(lambda: self._invert_all_checkboxes())
        btn_layout.addWidget(invert_btn)
        
        layout.addWidget(scroll)
        layout.addLayout(btn_layout)
        
        # 确定按钮
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._apply_selection)
        layout.addWidget(ok_btn)
    
    def _load_tools_from_agent(self):
        """从 Agent 加载工具启用/禁用状态"""
        if not self.agent_instance:
            # 如果没有 agent 实例，所有工具默认启用
            return
        
        enabled_tools = self.agent_instance.mcp_tools_enabled
        disabled_tools = self.agent_instance.mcp_tools_disabled
        
        # 如果 enabled_tools 为空，表示全部启用（除非在 disabled 中）
        if not enabled_tools:
            # 全部启用的情况：只有 disabled_tools 中的才被禁用
            for namespace, cbs in self.method_checkboxes.items():
                for cb in cbs:
                    tool_name = cb.property('tool_name')
                    if tool_name in disabled_tools:
                        cb.setChecked(False)
                    else:
                        cb.setChecked(True)
        else:
            # 有明确的启用列表：只有 enabled_tools 中的才被启用
            for namespace, cbs in self.method_checkboxes.items():
                for cb in cbs:
                    tool_name = cb.property('tool_name')
                    if tool_name in enabled_tools:
                        cb.setChecked(True)
                    else:
                        cb.setChecked(False)
    
    def _set_all_checkboxes(self, state: bool):
        """设置所有复选框的状态"""
        for namespace, cbs in self.method_checkboxes.items():
            for cb in cbs:
                cb.setChecked(state)
    
    def _invert_all_checkboxes(self):
        """反选所有复选框"""
        for namespace, cbs in self.method_checkboxes.items():
            for cb in cbs:
                cb.setChecked(not cb.isChecked())
    
    def _apply_selection(self):
        """应用 MCP 工具的选择状态"""
        enabled_tools = []
        disabled_tools = []
        
        # 收集所有选中的工具
        for namespace, cbs in self.method_checkboxes.items():
            for cb in cbs:
                tool_name = cb.property('tool_name')
                if cb.isChecked():
                    enabled_tools.append(tool_name)
                else:
                    disabled_tools.append(tool_name)
        
        # 发射信号
        self.tools_selection_changed.emit(enabled_tools, disabled_tools)
        
        print(f"[MCP 工具管理] 已启用 {len(enabled_tools)} 个工具，禁用 {len(disabled_tools)} 个工具")
        self.accept()
    
    def get_selected_tools(self):
        """
        获取当前选择的工具
        
        Returns:
            tuple: (enabled_tools, disabled_tools)
        """
        enabled_tools = []
        disabled_tools = []
        
        for namespace, cbs in self.method_checkboxes.items():
            for cb in cbs:
                tool_name = cb.property('tool_name')
                if cb.isChecked():
                    enabled_tools.append(tool_name)
                else:
                    disabled_tools.append(tool_name)
        
        return enabled_tools, disabled_tools
