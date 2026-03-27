"""
邮箱工具插件 - 拉取历史邮件对话框
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, 
    QPushButton, QMessageBox
)
from PySide6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

# Initialize plugin i18n
from app_qt.plugin_i18n import PluginI18n
_i18n = PluginI18n("email_utils", Path(__file__).parent.parent)
_ = _i18n.gettext


class FetchHistoryDialog(QDialog):
    """拉取历史邮件对话框"""
    
    def __init__(self, parent=None, default_days=60):
        super().__init__(parent)
        self.setWindowTitle(_("Fetch History Emails"))
        self.setMinimumWidth(300)
        self.selected_days = None
        
        self.init_ui(default_days)
    
    def init_ui(self, default_days):
        """初始化界面"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 说明文字
        info_label = QLabel(_("Enter days of history to fetch:") + ":")
        layout.addWidget(info_label)
        
        # 天数输入
        days_layout = QHBoxLayout()
        days_layout.addWidget(QLabel(_("Days:") + ":"))
        
        self.days_spinbox = QSpinBox()
        self.days_spinbox.setRange(1, 3650)  # 最多10年
        self.days_spinbox.setValue(default_days)
        self.days_spinbox.setSuffix(" " + _("days"))
        days_layout.addWidget(self.days_spinbox)
        
        layout.addLayout(days_layout)
        
        # 提示文字
        tip_label = QLabel(_("Will fetch all emails from last {} days, this may take some time.").format(default_days))
        tip_label.setWordWrap(True)
        tip_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(tip_label)
        
        layout.addSpacing(10)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton(_("Cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton(_("OK"))
        self.ok_btn.clicked.connect(self.on_ok)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
    
    def on_ok(self):
        """确定按钮点击"""
        self.selected_days = self.days_spinbox.value()
        
        if self.selected_days < 1:
            QMessageBox.warning(self, _("Warning"), _("Days must be greater than 0"))
            return
        
        self.accept()
    
    def get_days(self):
        """获取选择的天数"""
        return self.selected_days
