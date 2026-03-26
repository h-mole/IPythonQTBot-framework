"""
设置面板 Widget - 提供独立的配置界面
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
    QScrollArea,
    QMessageBox,
    QDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app_qt.configs import MainAppConfigSettings


class SettingsDialog(QDialog):
    """独立的设置对话框（模态）"""
    
    # 配置保存信号
    config_saved = Signal()
    
    def __init__(self, settings: MainAppConfigSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setObjectName("settingsDialog")
        
        # 设置对话框属性
        self.setWindowTitle("⚙️ 系统设置")
        self.setMinimumSize(900, 700)
        self.resize(1000, 800)
        
        # 设置为模态对话框
        self.setWindowModality(Qt.ApplicationModal)
        
        # 设置对话框布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 初始化 UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化用户界面"""
        # ===== 标题区域 =====
        title_label = QLabel("⚙️ 系统设置")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #e0e0e0;")
        line.setFixedHeight(2)
        
        # ===== 按钮区域 =====
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        # 保存按钮
        self.save_button = QPushButton("💾 保存配置")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.save_button.clicked.connect(self._save_config)
        btn_layout.addWidget(self.save_button)
        
        # 重置按钮
        self.reset_button = QPushButton("🔄 重置")
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c1170a;
            }
        """)
        self.reset_button.clicked.connect(self._reset_config)
        btn_layout.addWidget(self.reset_button)
        
        btn_layout.addStretch()
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #9e9e9e;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        close_button.clicked.connect(self.accept)
        btn_layout.addWidget(close_button)
        
        # ===== 添加到主布局 =====
        main_layout = self.layout()
        main_layout.addWidget(title_label)
        main_layout.addWidget(line)
        main_layout.addLayout(btn_layout)
        
        # ===== 设置表单区域 =====
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea { 
                background-color: transparent; 
                border: none; 
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        
        # 创建表单（使用 create_form_widget 避免嵌套滚动区域）
        self.settings_form = self.settings.create_form_widget()
        self.settings_form.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
            QGroupBox {
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        scroll_area.setWidget(self.settings_form)
        
        main_layout.addWidget(scroll_area, 1)  # stretch=1 让表单占据剩余空间
    
    def _save_config(self):
        """保存配置"""
        try:
            self.settings._save_settings()
            self.config_saved.emit()
            
            # 显示成功提示
            QMessageBox.information(
                self,
                "保存成功",
                f"配置已成功保存, 文件路径：{self.settings._config_file}！"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "保存失败",
                f"保存配置时出错：{str(e)}"
            )
    
    def _reset_config(self):
        """重置配置"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置所有配置吗？这将恢复到上次保存的状态。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 重新加载配置
                self.settings.__class__.load(
                    config_file=self.settings._config_file,
                    auto_create=False
                )
                
                # 重新创建表单
                self.settings_form = self.settings.create_form_widget()
                self.settings_form.setStyleSheet("""
                    QWidget {
                        background-color: transparent;
                    }
                    QGroupBox {
                        border: 1px solid #e0e0e0;
                        border-radius: 5px;
                        margin-top: 10px;
                        padding: 10px;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        left: 10px;
                        padding: 0 5px;
                    }
                """)
                scroll_area = self.findChild(QScrollArea)
                if scroll_area:
                    scroll_area.setWidget(self.settings_form)
                
                QMessageBox.information(
                    self,
                    "重置成功",
                    "配置已重置！"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "重置失败",
                    f"重置配置时出错：{str(e)}"
                )


class UnconfiguredDialog(QDialog):
    """未配置提示对话框（非模态）"""
    
    def __init__(self, settings: MainAppConfigSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("需要配置 LLM 提供商")
        self.setModal(False)  # 非模态对话框
        self.setMinimumSize(500, 300)
        
        # 初始化 UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("⚠️ 尚未配置 LLM 提供商")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 说明文字
        info_label = QLabel(
            "您还没有配置 LLM 提供商信息。\n\n"
            "为了正常使用相关功能，请先完成以下配置：\n"
            "• 添加 LLM 提供商（如 OpenAI、Azure 等）\n"
            "• 设置 API Key\n"
            "• 设置 API URL\n"
            "• 选择默认提供商和模型\n\n"
            "配置完成后点击'保存配置'按钮。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info_label)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        # 稍后配置按钮
        later_button = QPushButton("稍后配置")
        later_button.clicked.connect(self.close)
        btn_layout.addWidget(later_button)
        
        # 立即配置按钮
        config_button = QPushButton("立即配置 ➡️")
        config_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        config_button.clicked.connect(self._open_settings)
        btn_layout.addWidget(config_button)
        
        layout.addLayout(btn_layout)
    
    def _open_settings(self):
        """打开设置面板"""
        # 通过信号通知主窗口打开设置面板
        self.accept()
        # 主窗口会监听这个信号并打开设置面板


def check_and_show_unconfigured_dialog(settings: MainAppConfigSettings, parent=None) -> bool:
    """
    检查是否已配置，如果未配置则显示提示对话框
    
    Returns:
        bool: 如果已配置返回 True，否则返回 False
    """
    if not settings.is_provider_configured():
        dialog = UnconfiguredDialog(settings, parent)
        dialog.show()
        return False
    return True
