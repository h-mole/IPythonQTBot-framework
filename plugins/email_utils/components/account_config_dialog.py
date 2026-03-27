"""
邮箱工具插件 - 账号配置对话框组件
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QListWidget, QListWidgetItem, QPushButton,
    QLabel, QLineEdit, QDialogButtonBox, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt
from qtpy.QtWidgets import QCheckBox as QtCheckBox
import logging

logger = logging.getLogger(__name__)

# Initialize plugin i18n
from app_qt.plugin_i18n import PluginI18n
_i18n = PluginI18n("email_utils", Path(__file__).parent.parent)
_ = _i18n.gettext


class EmailAccountDialog(QDialog):
    """邮箱账号编辑对话框"""
    
    def __init__(self, parent=None, account_data=None):
        super().__init__(parent)
        self.account_data = account_data
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle(_("Email Account Configuration"))
        self.setMinimumWidth(500)
        
        layout = QFormLayout()
        self.setLayout(layout)
        
        # 账号名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(_("e.g., Work Email, Personal Gmail"))
        if self.account_data:
            self.name_edit.setText(self.account_data.get('name', ''))
        layout.addRow(_("Account Name:") + ":", self.name_edit)
        
        # 邮箱地址
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("your@email.com")
        if self.account_data:
            self.username_edit.setText(self.account_data.get('username', ''))
        layout.addRow(_("Email Address:") + ":", self.username_edit)
        
        # 密码
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText(_("Email password or auth code"))
        if self.account_data:
            self.password_edit.setText(self.account_data.get('password', ''))
        layout.addRow(_("Password/Auth Code:") + ":", self.password_edit)
        
        # IMAP 服务器
        self.imap_server_edit = QLineEdit()
        self.imap_server_edit.setPlaceholderText(_("e.g., imap.gmail.com"))
        if self.account_data:
            self.imap_server_edit.setText(self.account_data.get('imap_server', ''))
        layout.addRow(_("IMAP Server:") + ":", self.imap_server_edit)
        
        # IMAP 端口
        self.imap_port_edit = QLineEdit()
        self.imap_port_edit.setPlaceholderText("993")
        if self.account_data:
            self.imap_port_edit.setText(str(self.account_data.get('imap_port', 993)))
        layout.addRow(_("IMAP Port:") + ":", self.imap_port_edit)
        
        # SMTP 服务器
        self.smtp_server_edit = QLineEdit()
        self.smtp_server_edit.setPlaceholderText(_("e.g., smtp.gmail.com"))
        if self.account_data:
            self.smtp_server_edit.setText(self.account_data.get('smtp_server', ''))
        layout.addRow(_("SMTP Server:") + ":", self.smtp_server_edit)
        
        # SMTP 端口
        self.smtp_port_edit = QLineEdit()
        self.smtp_port_edit.setPlaceholderText("587")
        if self.account_data:
            self.smtp_port_edit.setText(str(self.account_data.get('smtp_port', 587)))
        layout.addRow(_("SMTP Port:") + ":", self.smtp_port_edit)
        
        # 使用 SSL
        self.use_ssl_check = QCheckBox(_("Use SSL/TLS"))
        self.use_ssl_check.setChecked(True)
        if self.account_data:
            self.use_ssl_check.setChecked(self.account_data.get('use_ssl', True))
        layout.addRow(self.use_ssl_check)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
    
    def get_account_data(self):
        """获取账号数据"""
        return {
            'name': self.name_edit.text().strip(),
            'username': self.username_edit.text().strip(),
            'password': self.password_edit.text().strip(),
            'imap_server': self.imap_server_edit.text().strip(),
            'imap_port': int(self.imap_port_edit.text()) if self.imap_port_edit.text() else 993,
            'smtp_server': self.smtp_server_edit.text().strip(),
            'smtp_port': int(self.smtp_port_edit.text()) if self.smtp_port_edit.text() else 587,
            'use_ssl': self.use_ssl_check.isChecked(),
        }


class AccountConfigDialog(QDialog):
    """账号配置对话框"""
    
    def __init__(self, parent=None, accounts_config=None):
        super().__init__(parent)
        self.accounts_config = accounts_config or []
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle(_("Email Account Configuration"))
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 账号列表
        list_group = QGroupBox(_("Configured Accounts"))
        list_layout = QVBoxLayout()
        list_group.setLayout(list_layout)
        
        self.accounts_list = QListWidget()
        self.accounts_list.setSelectionMode(QListWidget.SingleSelection)
        
        for acc in self.accounts_config:
            name = acc.get('name', '')
            username = acc.get('username', '')
            self.accounts_list.addItem(f"{name} ({username})")
        
        list_layout.addWidget(self.accounts_list)
        
        # 账号操作按钮
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ " + _("Add Account"))
        add_btn.clicked.connect(self.add_account)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("✏️ " + _("Edit Account"))
        edit_btn.clicked.connect(self.edit_account)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ " + _("Delete Account"))
        delete_btn.clicked.connect(self.delete_account)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        list_layout.addLayout(btn_layout)
        
        layout.addWidget(list_group)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def add_account(self):
        """添加账号"""
        dialog = EmailAccountDialog(self)
        if dialog.exec() == int(QDialog.DialogCode.Accepted):
            account_data = dialog.get_account_data()
            self.accounts_config.append(account_data)
            self.accounts_list.addItem(f"{account_data['name']} ({account_data['username']})")
    
    def edit_account(self):
        """编辑账号"""
        selected_row = self.accounts_list.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, _("Warning"), _("Please select an account to edit!"))
            return
        
        account_data = self.accounts_config[selected_row].copy()
        dialog = EmailAccountDialog(self, account_data)
        if dialog.exec() == int(QDialog.DialogCode.Accepted):
            updated_data = dialog.get_account_data()
            self.accounts_config[selected_row] = updated_data
            
            # 更新列表显示
            item = self.accounts_list.item(selected_row)
            item.setText(f"{updated_data['name']} ({updated_data['username']})")
    
    def delete_account(self):
        """删除账号"""
        selected_row = self.accounts_list.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, _("Warning"), _("Please select an account to delete!"))
            return
        
        reply = QMessageBox.question(
            self,
            _("Confirm Delete"),
            _("Are you sure to delete the selected account?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.accounts_config.pop(selected_row)
            self.accounts_list.takeItem(selected_row)
