"""
邮箱工具插件 - 邮件详情对话框组件
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox,
    QListWidget, QPushButton, QLabel, QTextBrowser,
    QDialogButtonBox, QMessageBox, QFileDialog,
    QListWidgetItem, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QThread
import logging

logger = logging.getLogger(__name__)


class DownloadAttachmentWorker(QThread):
    """后台下载附件线程"""
    
    download_completed = Signal(str)  # 信号：下载完成（返回保存路径）
    error_occurred = Signal(str)      # 信号：发生错误
    
    def __init__(self, account_name, email_id, filename, save_path):
        super().__init__()
        self.account_name = account_name
        self.email_id = email_id
        self.filename = filename
        self.save_path = save_path
        
    def run(self):
        """线程运行方法"""
        try:
            from ..core.email_client import EmailClient
            from ..utils.helpers import get_account_config
            
            account_config = get_account_config(self.account_name)
            client = EmailClient(account_config)
            
            success = client.download_attachment(
                self.account_name,
                self.email_id,
                self.filename,
                self.save_path
            )
            if success:
                self.download_completed.emit(self.save_path)
            else:
                self.error_occurred.emit("下载失败")
        except Exception as e:
            logger.error(f"Error downloading attachment: {e}", exc_info=True)
            self.error_occurred.emit(str(e))


class EmailDetailDialog(QDialog):
    """邮件详情对话框"""
    
    def __init__(self, parent=None, email_detail=None, account_name=None):
        super().__init__(parent)
        self.email_detail = email_detail
        self.account_name = account_name
        self.plugin_manager = parent.plugin_manager if hasattr(parent, 'plugin_manager') else None
        self.download_worker = None
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("邮件详情")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 邮件信息区域
        info_group = QGroupBox("邮件信息")
        info_layout = QFormLayout()
        info_group.setLayout(info_layout)
        
        # 主题
        subject_label = QLabel(self.email_detail.get('subject', ''))
        subject_label.setWordWrap(True)
        info_layout.addRow("主题:", subject_label)
        
        # 发件人
        from_label = QLabel(self.email_detail.get('from', ''))
        info_layout.addRow("发件人:", from_label)
        
        # 收件人
        to_label = QLabel(self.email_detail.get('to', ''))
        info_layout.addRow("收件人:", to_label)
        
        # 日期
        date_label = QLabel(self.email_detail.get('date', ''))
        info_layout.addRow("日期:", date_label)
        
        layout.addWidget(info_group)
        
        # 邮件正文（使用富文本浏览器）
        body_group = QGroupBox("邮件正文")
        body_layout = QVBoxLayout()
        body_group.setLayout(body_layout)
        
        self.body_browser = QTextBrowser()
        self.body_browser.setOpenExternalLinks(True)
        # 优先显示 HTML，如果没有则显示纯文本
        body_html = self.email_detail.get('body_html', '')
        body_plain = self.email_detail.get('body_plain', '')
        if body_html:
            self.body_browser.setHtml(body_html)
        else:
            self.body_browser.setPlainText(body_plain)
        body_layout.addWidget(self.body_browser)
        
        layout.addWidget(body_group)
        
        # 附件区域
        attachments = self.email_detail.get('attachments', [])
        if attachments:
            attach_group = QGroupBox(f"附件 ({len(attachments)})")
            attach_layout = QVBoxLayout()
            attach_group.setLayout(attach_layout)
            
            self.attach_list = QListWidget()
            self.attach_list.setSelectionMode(QAbstractItemView.SingleSelection)
            
            for attach in attachments:
                item_text = f"{attach['filename']} ({self.format_size(attach['size'])})"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, attach['filename'])
                self.attach_list.addItem(item)
            
            attach_layout.addWidget(self.attach_list)
            
            # 下载按钮
            download_btn = QPushButton("⬇️ 下载选中附件")
            download_btn.clicked.connect(self.start_download)
            attach_layout.addWidget(download_btn)
            
            layout.addWidget(attach_group)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def format_size(self, size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def start_download(self):
        """开始下载（在后台线程中）"""
        selected_items = self.attach_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要下载的附件！")
            return
        
        filename = selected_items[0].data(Qt.UserRole)
        
        # 选择保存路径
        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存附件", filename, "All Files (*)"
        )
        
        if save_path:
            # 创建后台下载线程
            self.download_worker = DownloadAttachmentWorker(
                self.account_name,
                self.email_detail['id'],
                filename,
                save_path
            )
            self.download_worker.download_completed.connect(self.on_download_completed)
            self.download_worker.error_occurred.connect(self.on_download_error)
            self.download_worker.start()
    
    def on_download_completed(self, save_path):
        """下载完成的回调"""
        QMessageBox.information(self, "成功", f"附件已保存到:\n{save_path}")
    
    def on_download_error(self, error_msg):
        """下载错误的回调"""
        QMessageBox.critical(self, "错误", f"下载失败：{error_msg}")
