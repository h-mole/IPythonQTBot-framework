"""
邮箱工具插件 - 发送邮件对话框组件
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QListWidget, QPushButton, QLabel,
    QLineEdit, QTextEdit, QDialogButtonBox, QMessageBox,
    QFileDialog, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtCore import Signal, QThread
import logging

logger = logging.getLogger(__name__)

# Initialize plugin i18n
from app_qt.plugin_i18n import PluginI18n
_i18n = PluginI18n("email_utils", Path(__file__).parent.parent)
_ = _i18n.gettext


class SendEmailWorker(QThread):
    """后台发送邮件线程"""
    
    send_completed = Signal(bool)  # 信号：发送完成
    error_occurred = Signal(str)   # 信号：发生错误
    
    def __init__(self, account_name, to, subject, body, attachments=None):
        super().__init__()
        self.account_name = account_name
        self.to = to
        self.subject = subject
        self.body = body
        self.attachments = attachments or []
        
    def run(self):
        """线程运行方法"""
        try:
            from ..core.email_client import EmailClient
            from ..utils.helpers import get_account_config
            
            account_config = get_account_config(self.account_name)
            client = EmailClient(account_config)
            
            success = client.send_email(
                to=self.to,
                subject=self.subject,
                body=self.body,
                attachments=self.attachments
            )
            self.send_completed.emit(success)
        except Exception as e:
            logger.error(f"Error sending email: {e}", exc_info=True)
            self.error_occurred.emit(str(e))


class SendEmailDialog(QDialog):
    """发送邮件对话框"""
    
    def __init__(self, parent=None, account_name=None, reply_mode=False, 
                 reply_to_email=None, reply_subject=None, reply_body=None):
        """
        初始化发送邮件对话框
        
        Args:
            parent: 父窗口
            account_name: 发件账号名称
            reply_mode: 是否为回复模式
            reply_to_email: 回复对象的邮箱地址
            reply_subject: 回复主题（会自动添加 Re: 前缀）
            reply_body: 引用的原文内容（HTML格式）
        """
        super().__init__(parent)
        self.account_name = account_name
        self.plugin_manager = parent.plugin_manager if hasattr(parent, 'plugin_manager') else None
        self.attachments = []
        self.send_worker = None
        
        # 回复模式相关
        self.reply_mode = reply_mode
        self.reply_to_email = reply_to_email
        self.reply_subject = reply_subject
        self.reply_body = reply_body
        
        # 防止重复发送的标志
        self._is_sending = False
        
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        # 根据模式设置窗口标题
        if self.reply_mode:
            self.setWindowTitle(_("Reply Email"))
        else:
            self.setWindowTitle(_("Send Email"))
        self.setMinimumSize(700, 600)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 表单布局
        form_layout = QFormLayout()
        
        # 发件人
        self.from_combo = QComboBox()
        self.from_combo.setEditable(True)
        # 这里应该从配置中加载账号
        if self.account_name:
            self.from_combo.addItem(self.account_name)
        form_layout.addRow(_("From:") + ":", self.from_combo)
        
        # 收件人
        self.to_edit = QLineEdit()
        if self.reply_mode and self.reply_to_email:
            self.to_edit.setText(self.reply_to_email)
            self.to_edit.setReadOnly(True)  # 回复模式下收件人只读
        else:
            self.to_edit.setPlaceholderText(_("Multiple recipients separated by commas"))
        form_layout.addRow(_("To:") + ":", self.to_edit)
        
        # 主题
        self.subject_edit = QLineEdit()
        if self.reply_mode and self.reply_subject:
            # 添加 Re: 前缀
            if self.reply_subject.startswith('Re:'):
                self.subject_edit.setText(self.reply_subject)
            else:
                self.subject_edit.setText(f"Re: {self.reply_subject}")
            self.subject_edit.setReadOnly(True)  # 回复模式下主题只读
        form_layout.addRow(_("Subject:") + ":", self.subject_edit)
        
        layout.addLayout(form_layout)
        
        # 正文（支持 HTML）
        body_label = QLabel(_("Body (HTML supported):") + ":")
        layout.addWidget(body_label)
        
        self.body_edit = QTextEdit()
        if self.reply_mode and self.reply_body:
            # 预填充引用原文的内容
            self.body_edit.setHtml(self.reply_body)
        else:
            self.body_edit.setHtml("<p><br></p>")
        layout.addWidget(self.body_edit)
        
        # 附件列表
        attach_group = QGroupBox(_("Attachments"))
        attach_layout = QVBoxLayout()
        attach_group.setLayout(attach_layout)
        
        self.attach_list = QListWidget()
        attach_layout.addWidget(self.attach_list)
        
        # 附件按钮
        btn_layout = QHBoxLayout()
        add_attach_btn = QPushButton("➕ " + _("Add Attachment"))
        add_attach_btn.clicked.connect(self.add_attachment)
        btn_layout.addWidget(add_attach_btn)
        
        remove_attach_btn = QPushButton("🗑️ " + _("Remove Attachment"))
        remove_attach_btn.clicked.connect(self.remove_attachment)
        btn_layout.addWidget(remove_attach_btn)
        
        btn_layout.addStretch()
        attach_layout.addLayout(btn_layout)
        
        layout.addWidget(attach_group)
        
        # 发送按钮
        send_btn = QPushButton("📨 " + _("Send Email"))
        send_btn.clicked.connect(self.start_send_email)
        layout.addWidget(send_btn)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.start_send_email)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def add_attachment(self):
        """添加附件"""
        files, _ = QFileDialog.getOpenFileNames(self, "选择附件", "", "All Files (*)")
        if files:
            self.attachments.extend(files)
            self.update_attach_list()
    
    def remove_attachment(self):
        """移除附件"""
        selected_items = self.attach_list.selectedItems()
        for item in selected_items:
            row = self.attach_list.row(item)
            self.attach_list.takeItem(row)
            if row < len(self.attachments):
                self.attachments.pop(row)
        self.update_attach_list()
    
    def update_attach_list(self):
        """更新附件列表显示"""
        self.attach_list.clear()
        for file_path in self.attachments:
            filename = os.path.basename(file_path)
            size = os.path.getsize(file_path)
            size_str = f"{size / 1024:.2f} KB" if size < 1024*1024 else f"{size / (1024*1024):.2f} MB"
            self.attach_list.addItem(f"{filename} ({size_str})")
    
    def start_send_email(self):
        """开始发送邮件（在后台线程中）"""
        # 防止重复发送
        if self._is_sending:
            QMessageBox.information(self, _("Info"), _("Email is being sent, please wait..."))
            return
        
        to = self.to_edit.text().strip()
        subject = self.subject_edit.text().strip()
        body = self.body_edit.toHtml()
        
        if not to:
            QMessageBox.warning(self, _("Warning"), _("Please enter recipient address!"))
            return
        
        if not subject:
            QMessageBox.warning(self, _("Warning"), _("Please enter email subject!"))
            return
        
        # 设置发送中标志
        self._is_sending = True
        
        # 禁用发送按钮防止重复点击
        self.setEnabled(False)
        
        # 获取发件人账号配置
        account_name = self.from_combo.currentText()
        
        # 创建后台发送线程
        self.send_worker = SendEmailWorker(
            account_name=account_name,
            to=to,
            subject=subject,
            body=body,
            attachments=self.attachments
        )
        self.send_worker.send_completed.connect(self.on_send_completed)
        self.send_worker.error_occurred.connect(self.on_send_error)
        self.send_worker.finished.connect(self.on_send_finished)
        self.send_worker.start()
    
    def on_send_finished(self):
        """线程结束后的清理"""
        self._is_sending = False
        self.setEnabled(True)
    
    def on_send_completed(self, success):
        """发送完成的回调"""
        # 等待线程完全结束，避免 QThread destroyed while running 错误
        if self.send_worker and self.send_worker.isRunning():
            self.send_worker.wait(5000)  # 最多等待5秒
        
        if success:
            QMessageBox.information(self, _("Success"), _("Email sent successfully!"))
            self.accept()
        else:
            QMessageBox.warning(self, _("Warning"), _("Failed to send email!"))
    
    def on_send_error(self, error_msg):
        """发送错误的回调"""
        # 等待线程完全结束
        if self.send_worker and self.send_worker.isRunning():
            self.send_worker.wait(5000)
        
        QMessageBox.critical(self, _("Error"), _("Failed to send: {}") + error_msg)
    
    def closeEvent(self, event):
        """关闭事件处理 - 确保线程安全结束"""
        if self.send_worker and self.send_worker.isRunning():
            # 如果线程还在运行，等待它完成
            self.send_worker.wait(3000)  # 等待最多3秒
        event.accept()
