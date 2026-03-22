"""
测试 MCP 工具管理器组件
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from app_qt.widgets.mcp_tools_manager import MCPToolsManagerWidget


class TestWindow(QMainWindow):
    """测试窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MCP 工具管理器测试")
        self.setGeometry(100, 100, 400, 300)
        
        # 创建中心 widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 布局
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # 打开对话框按钮
        btn = QPushButton("打开 MCP 工具管理器")
        btn.clicked.connect(self.open_mcp_manager)
        layout.addWidget(btn)
        
        # 模拟的 Agent 实例（用于测试）
        class MockAgent:
            def __init__(self):
                self.mcp_tools_enabled = set()  # 空表示全部启用
                self.mcp_tools_disabled = {"text_helper.get_text"}  # 禁用一个工具
        
        self.mock_agent = MockAgent()
    
    def open_mcp_manager(self):
        """打开 MCP 工具管理器"""
        dialog = MCPToolsManagerWidget(parent=self, agent_instance=self.mock_agent)
        
        # 连接信号
        def on_selection_changed(enabled, disabled):
            print(f"\n[测试] 用户确认选择:")
            print(f"  启用的工具：{len(enabled)} 个")
            print(f"  禁用的工具：{len(disabled)} 个")
            if enabled:
                print(f"    - {', '.join(enabled[:5])}{'...' if len(enabled) > 5 else ''}")
            if disabled:
                print(f"    - {', '.join(disabled[:5])}{'...' if len(disabled) > 5 else ''}")
        
        dialog.tools_selection_changed.connect(on_selection_changed)
        dialog.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    print("=" * 60)
    print("MCP 工具管理器测试")
    print("=" * 60)
    print("说明:")
    print("1. 点击'打开 MCP 工具管理器'按钮")
    print("2. 观察复选框的初始状态（应该反映 MockAgent 的配置）")
    print("3. 修改选择并点击确定")
    print("4. 查看控制台输出的选择结果")
    print("=" * 60)
    
    sys.exit(app.exec())
