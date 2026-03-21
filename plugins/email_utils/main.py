"""
邮箱工具插件 - 主程序
提供邮件收发、管理和预览功能
"""

import os
import sys
import json
import email
import imaplib
import smtplib
import threading
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from bs4 import BeautifulSoup
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QPushButton,
    QLabel,
    QFrame,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QDialog,
    QLineEdit,
    QTextEdit,
    QFormLayout,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QMenu,
    QProgressBar,
    QStatusBar,
    QTextBrowser,
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QAction, QColor, QTextCursor
from app_qt.configs import PLUGIN_DATA_DIR
from qtpy.QtWidgets import QCheckBox
import logging
logger = logging.getLogger(__name__)
# 默认邮箱配置
DEFAULT_EMAIL_ACCOUNTS = []

# 插件数据目录
EMAIL_UTILS_DATA_DIR = os.path.join(PLUGIN_DATA_DIR, "email_utils")
CONFIG_FILE = os.path.join(EMAIL_UTILS_DATA_DIR, "email_accounts.json")


class EmailFetchWorker(QThread):
    """后台邮件拉取线程"""
    
    emails_fetched = Signal(list)  # 信号：邮件列表获取完成
    error_occurred = Signal(str)   # 信号：发生错误
    
    def __init__(self, account_config, limit=5):
        super().__init__()
        self.account_config = account_config
        self.limit = limit
        self.result = []
        
    def run(self):
        """线程运行方法"""
        try:
            emails = self.fetch_emails()
            logger.info(f"Fetched {len(emails)} emails: {emails} in thread")
            self.emails_fetched.emit(emails)
            self.result = emails
        except Exception as e:
            logger.error(f"Error fetching emails: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
    
    def fetch_emails(self):
        """从 IMAP 服务器获取邮件"""
        account_name = self.account_config.get('name')
        imap_server = self.account_config.get('imap_server')
        imap_port = self.account_config.get('imap_port', 993)
        username = self.account_config.get('username')
        password = self.account_config.get('password')
        use_ssl = self.account_config.get('use_ssl', True)
        
        emails = []
        
        # 连接 IMAP 服务器
        if use_ssl:
            mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        else:
            mail = imaplib.IMAP4(imap_server, imap_port)
        logger.info(f"Connected to IMAP server: {imap_server}:{imap_port}")
        # 登录
        mail.login(username, password)
        logger.info("Login to IMAP server successful")
        # 选择收件箱
        mail.select('inbox')
        logger.info("Selected inbox folder")
        # 搜索所有邮件
        status, messages = mail.search(None, 'ALL')
        logger.info("Search completed")
        # 获取最新的 N 封邮件
        email_ids = messages[0].split()
        recent_ids = email_ids[-self.limit:] if len(email_ids) > self.limit else email_ids
        logger.info(f"Retrieving {len(recent_ids)} emails")
        # 逆序排列（最新的在前）
        recent_ids = reversed(recent_ids)
        logger.info("Emails retrieved successfully")
        for email_id in recent_ids:
            try:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                raw_email = msg_data[0][1]
                logger.info(f"Retrieved email {email_id.decode()}")
                # 解析邮件
                email_obj = email.message_from_bytes(raw_email)
                # 提取主题
                subject = self.decode_header(email_obj.get('Subject', ''))
                # 提取发件人
                from_str = self.decode_header(email_obj.get('From', ''))
                # 提取日期
                date_str = email_obj.get('Date', '')
                try:
                    date_obj = email.utils.parsedate_to_datetime(date_str)
                    date_display = date_obj.strftime('%Y-%m-%d %H:%M')
                except:
                    date_display = date_str
                # 提取正文预览
                body_preview = self.get_email_body_preview(email_obj)
                
                # 检查是否有附件
                has_attachment = self.check_has_attachment(email_obj)
                logger.info(f"Checked for attachments in email {email_id.decode()}")
                emails.append({
                    'id': email_id.decode(),
                    'subject': subject,
                    'from': from_str,
                    'date': date_display,
                    'preview': body_preview[:100] + '...' if len(body_preview) > 100 else body_preview,
                    'has_attachment': has_attachment,
                })
            except Exception as e:
                print(f"解析邮件失败：{e}")
                continue
        
        # 关闭连接
        mail.close()
        mail.logout()
        
        return emails
    
    def decode_header(self, header):
        """解码邮件头"""
        decoded_parts = email.header.decode_header(header)
        decoded_str = ''
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    decoded_str += part.decode(encoding or 'utf-8', errors='replace')
                except:
                    decoded_str += part.decode('utf-8', errors='replace')
            else:
                decoded_str += part
        return decoded_str
    
    def get_email_body_preview(self, email_obj):
        """获取邮件正文预览"""
        body = ''
        
        # 如果是 multipart
        if email_obj.is_multipart():
            for part in email_obj.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # 优先获取 text/plain 或 text/html
                if content_type == 'text/plain' and 'attachment' not in content_disposition:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            body += payload.decode(charset, errors='replace')
                            break
                    except:
                        pass
                elif content_type == 'text/html' and not body:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            html = payload.decode(charset, errors='replace')
                            # 解析 HTML 提取纯文本
                            soup = BeautifulSoup(html, 'html.parser')
                            body += soup.get_text()
                            break
                    except:
                        pass
        else:
            # 不是 multipart
            try:
                payload = email_obj.get_payload(decode=True)
                if payload:
                    charset = email_obj.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
            except:
                pass
        
        return body.strip()
    
    def check_has_attachment(self, email_obj):
        """检查邮件是否有附件"""
        if email_obj.is_multipart():
            for part in email_obj.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get("Content-Disposition"):
                    return True
        return False


class EmailDetailWorker(QThread):
    """后台获取邮件详情线程"""
    
    detail_fetched = Signal(dict)  # 信号：邮件详情获取完成
    error_occurred = Signal(str)   # 信号：发生错误
    
    def __init__(self, account_name, email_id):
        super().__init__()
        self.account_name = account_name
        self.email_id = email_id
        
    def run(self):
        """线程运行方法"""
        try:
            detail = get_email_detail_api(self.account_name, self.email_id)
            self.detail_fetched.emit(detail)
        except Exception as e:
            logger.error(f"Error fetching email detail: {e}", exc_info=True)
            self.error_occurred.emit(str(e))


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
            success = download_attachment_api(
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
            success = send_email_api(
                self.account_name,
                self.to,
                self.subject,
                self.body,
                self.attachments
            )
            self.send_completed.emit(success)
        except Exception as e:
            logger.error(f"Error sending email: {e}", exc_info=True)
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
        self.body_browser.setHtml(self.email_detail.get('body_html', self.email_detail.get('body', '')))
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


class SendEmailDialog(QDialog):
    """发送邮件对话框"""
    
    def __init__(self, parent=None, account_name=None):
        super().__init__(parent)
        self.account_name = account_name
        self.plugin_manager = parent.plugin_manager if hasattr(parent, 'plugin_manager') else None
        self.attachments = []
        self.send_worker = None
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("发送邮件")
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
        form_layout.addRow("发件人:", self.from_combo)
        
        # 收件人
        self.to_edit = QLineEdit()
        self.to_edit.setPlaceholderText("多个收件人用逗号分隔")
        form_layout.addRow("收件人:", self.to_edit)
        
        # 主题
        self.subject_edit = QLineEdit()
        form_layout.addRow("主题:", self.subject_edit)
        
        layout.addLayout(form_layout)
        
        # 正文（支持 HTML）
        body_label = QLabel("正文（支持 HTML）:")
        layout.addWidget(body_label)
        
        self.body_edit = QTextEdit()
        self.body_edit.setHtml("<p><br></p>")
        layout.addWidget(self.body_edit)
        
        # 附件列表
        attach_group = QGroupBox("附件")
        attach_layout = QVBoxLayout()
        attach_group.setLayout(attach_layout)
        
        self.attach_list = QListWidget()
        attach_layout.addWidget(self.attach_list)
        
        # 附件按钮
        btn_layout = QHBoxLayout()
        add_attach_btn = QPushButton("➕ 添加附件")
        add_attach_btn.clicked.connect(self.add_attachment)
        btn_layout.addWidget(add_attach_btn)
        
        remove_attach_btn = QPushButton("🗑️ 移除附件")
        remove_attach_btn.clicked.connect(self.remove_attachment)
        btn_layout.addWidget(remove_attach_btn)
        
        btn_layout.addStretch()
        attach_layout.addLayout(btn_layout)
        
        layout.addWidget(attach_group)
        
        # 发送按钮
        send_btn = QPushButton("📨 发送邮件")
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
        to = self.to_edit.text().strip()
        subject = self.subject_edit.text().strip()
        body = self.body_edit.toHtml()
        
        if not to:
            QMessageBox.warning(self, "警告", "请输入收件人地址！")
            return
        
        if not subject:
            QMessageBox.warning(self, "警告", "请输入邮件主题！")
            return
        
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
        self.send_worker.start()
    
    def on_send_completed(self, success):
        """发送完成的回调"""
        if success:
            QMessageBox.information(self, "成功", "邮件发送成功！")
            self.accept()
        else:
            QMessageBox.warning(self, "警告", "发送失败！")
    
    def on_send_error(self, error_msg):
        """发送错误的回调"""
        QMessageBox.critical(self, "错误", f"发送失败：{error_msg}")


class EmailManagerTab(QWidget):
    """邮箱管理器标签页"""
    
    # 表格列定义
    COLUMNS = [
        "ID",
        "主题",
        "发件人",
        "日期",
        "预览",
        "附件",
    ]
    
    def __init__(self, plugin_manager=None):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.config_file = CONFIG_FILE
        self.emails_data = []
        self.current_account = None
        self.fetch_worker = None
        
        # 确保数据目录存在
        os.makedirs(EMAIL_UTILS_DATA_DIR, exist_ok=True)
        
        # 加载配置
        self.load_accounts_config()
        
        self.init_ui()
        
        # 如果有配置的账号，自动选择第一个
        if self.accounts_config:
            self.account_combo.setCurrentIndex(0)
            self.on_account_changed()
    
    def init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # 顶部控制区域
        control_frame = QFrame()
        control_layout = QHBoxLayout()
        control_frame.setLayout(control_layout)
        
        # 账号选择
        control_layout.addWidget(QLabel("邮箱账号:"))
        self.account_combo = QComboBox()
        self.account_combo.setMinimumWidth(200)
        self.account_combo.currentTextChanged.connect(self.on_account_changed)
        control_layout.addWidget(self.account_combo)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("🔄 刷新邮件")
        self.refresh_btn.clicked.connect(self.fetch_emails)
        control_layout.addWidget(self.refresh_btn)
        
        # 写邮件按钮
        self.compose_btn = QPushButton("📝 写邮件")
        self.compose_btn.clicked.connect(self.compose_email)
        control_layout.addWidget(self.compose_btn)
        
        # 账号配置按钮
        self.config_btn = QPushButton("⚙️ 账号配置")
        self.config_btn.clicked.connect(self.show_account_config)
        control_layout.addWidget(self.config_btn)
        
        control_layout.addStretch()
        
        main_layout.addWidget(control_frame)
        
        # 邮件列表
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        
        # 设置表格属性
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setMouseTracking(True)
        
        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 主题
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # 发件人
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 日期
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # 预览
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # 附件
        
        # 连接双击信号
        self.table.cellDoubleClicked.connect(self.view_email_detail)
        
        main_layout.addWidget(self.table)
        
        # 底部状态栏
        status_frame = QFrame()
        status_layout = QHBoxLayout()
        status_frame.setLayout(status_layout)
        
        self.status_label = QLabel("就绪")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(status_frame)
    
    def load_accounts_config(self):
        """加载账号配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.accounts_config = data.get("accounts", [])
            else:
                self.accounts_config = []
                # 创建默认配置文件
                self.save_accounts_config()
        except Exception as e:
            print(f"加载账号配置失败：{e}")
            self.accounts_config = []
    
    def save_accounts_config(self):
        """保存账号配置"""
        try:
            data = {"accounts": self.accounts_config}
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存账号配置失败：{e}")
    
    def on_account_changed(self):
        """账号改变时的处理"""
        account_name = self.account_combo.currentText()
        self.current_account = account_name
        
        # 自动刷新邮件
        self.fetch_emails()
    
    def update_account_combo(self):
        """更新账号下拉框"""
        current = self.account_combo.currentText()
        self.account_combo.clear()
        
        for account in self.accounts_config:
            name = account.get('name', '')
            if name:
                self.account_combo.addItem(name)
        
        # 尝试恢复之前的选择
        if current:
            index = self.account_combo.findText(current)
            if index >= 0:
                self.account_combo.setCurrentIndex(index)

    def fetch_emails(self):
        """获取邮件"""
        # 检查是否有配置的账号
        if not self.accounts_config or len(self.accounts_config) == 0:
            logger.warning("警告：请先配置邮箱账号，才能拉取！")
            QMessageBox.warning(self, "警告", "请先配置邮箱账号！")
            return
            
        # 如果没有当前账号，默认选择第一个
        if not self.current_account:
            self.current_account = self.accounts_config[0].get('name')
            logger.info(f"自动选择第一个账号：{self.current_account}")
            
        # 查找当前账号配置
        account_config = None
        for acc in self.accounts_config:
            if acc.get('name') == self.current_account:
                account_config = acc
                break
            
        if not account_config:
            logger.warning(f"警告：未找到账号 [{self.current_account}] 的配置！")
            QMessageBox.warning(self, "警告", "未找到当前账号的配置！")
            return
        
        # 显示进度
        self.status_label.setText("正在获取邮件...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        
        # 创建后台线程获取邮件
        self.fetch_worker = EmailFetchWorker(account_config, limit=20)
        self.fetch_worker.emails_fetched.connect(self.on_emails_fetched)
        self.fetch_worker.error_occurred.connect(self.on_fetch_error)
        self.fetch_worker.start()
    
    def on_emails_fetched(self, emails):
        """邮件获取完成的回调"""
        self.emails_data = emails
        self.refresh_table()
        
        self.status_label.setText(f"已获取 {len(emails)} 封邮件")
        self.progress_bar.setVisible(False)
    
    def on_fetch_error(self, error_msg):
        """获取邮件错误的回调"""
        self.status_label.setText("获取失败")
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "错误", f"获取邮件失败：{error_msg}")
    
    def refresh_table(self):
        """刷新表格显示"""
        self.table.setRowCount(0)
        
        for email_data in self.emails_data:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            
            # ID
            self.table.setItem(row_position, 0, QTableWidgetItem(str(email_data.get('id', ''))))
            
            # 主题
            subject_item = QTableWidgetItem(email_data.get('subject', ''))
            subject_item.setToolTip(email_data.get('subject', ''))
            self.table.setItem(row_position, 1, subject_item)
            
            # 发件人
            self.table.setItem(row_position, 2, QTableWidgetItem(email_data.get('from', '')))
            
            # 日期
            self.table.setItem(row_position, 3, QTableWidgetItem(email_data.get('date', '')))
            
            # 预览
            preview_item = QTableWidgetItem(email_data.get('preview', ''))
            preview_item.setToolTip(email_data.get('preview', ''))
            self.table.setItem(row_position, 4, preview_item)
            
            # 附件
            attach_item = QTableWidgetItem("📎" if email_data.get('has_attachment') else "")
            attach_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_position, 5, attach_item)
    
    def view_email_detail(self, row, column):
        """查看邮件详情（异步获取）"""
        if row >= len(self.emails_data):
            return
        
        email_data = self.emails_data[row]
        email_id = email_data.get('id')
        
        if not email_id:
            return
        
        # 创建后台获取详情线程
        self.detail_worker = EmailDetailWorker(self.current_account, email_id)
        self.detail_worker.detail_fetched.connect(self.show_email_detail_dialog)
        self.detail_worker.error_occurred.connect(self.on_get_detail_error)
        self.detail_worker.start()
    
    def show_email_detail_dialog(self, email_detail):
        """显示邮件详情对话框"""
        dialog = EmailDetailDialog(self, email_detail, self.current_account)
        dialog.exec()
    
    def on_get_detail_error(self, error_msg):
        """获取邮件详情错误的回调"""
        QMessageBox.critical(self, "错误", f"获取邮件详情失败：{error_msg}")
    
    def compose_email(self):
        """撰写新邮件"""
        if not self.current_account:
            QMessageBox.warning(self, "警告", "请先选择邮箱账号！")
            return
        
        dialog = SendEmailDialog(self, self.current_account)
        dialog.exec()
    
    def show_account_config(self):
        """显示账号配置对话框"""
        dialog = AccountConfigDialog(self, self.accounts_config)
        if dialog.exec() == int(QDialog.DialogCode.Accepted):
            self.accounts_config = dialog.accounts_config
            self.save_accounts_config()
            self.update_account_combo()


class AccountConfigDialog(QDialog):
    """账号配置对话框"""
    
    def __init__(self, parent=None, accounts_config=None):
        super().__init__(parent)
        self.accounts_config = accounts_config or []
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("邮箱账号配置")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 账号列表
        list_group = QGroupBox("已配置的账号")
        list_layout = QVBoxLayout()
        list_group.setLayout(list_layout)
        
        self.accounts_list = QListWidget()
        self.accounts_list.setSelectionMode(QAbstractItemView.SingleSelection)
        
        for acc in self.accounts_config:
            name = acc.get('name', '')
            username = acc.get('username', '')
            self.accounts_list.addItem(f"{name} ({username})")
        
        list_layout.addWidget(self.accounts_list)
        
        # 账号操作按钮
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ 添加账号")
        add_btn.clicked.connect(self.add_account)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("✏️ 编辑账号")
        edit_btn.clicked.connect(self.edit_account)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ 删除账号")
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
            QMessageBox.warning(self, "警告", "请先选择要编辑的账号！")
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
            QMessageBox.warning(self, "警告", "请先选择要删除的账号！")
            return
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除选中的账号吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.accounts_config.pop(selected_row)
            self.accounts_list.takeItem(selected_row)


class EmailAccountDialog(QDialog):
    """邮箱账号编辑对话框"""
    
    def __init__(self, parent=None, account_data=None):
        super().__init__(parent)
        self.account_data = account_data
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("邮箱账号配置")
        self.setMinimumWidth(500)
        
        layout = QFormLayout()
        self.setLayout(layout)
        
        # 账号名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：公司邮箱、个人 Gmail")
        if self.account_data:
            self.name_edit.setText(self.account_data.get('name', ''))
        layout.addRow("账号名称:", self.name_edit)
        
        # 邮箱地址
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("your@email.com")
        if self.account_data:
            self.username_edit.setText(self.account_data.get('username', ''))
        layout.addRow("邮箱地址:", self.username_edit)
        
        # 密码
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("邮箱密码或授权码")
        if self.account_data:
            self.password_edit.setText(self.account_data.get('password', ''))
        layout.addRow("密码/授权码:", self.password_edit)
        
        # IMAP 服务器
        self.imap_server_edit = QLineEdit()
        self.imap_server_edit.setPlaceholderText("例如：imap.gmail.com")
        if self.account_data:
            self.imap_server_edit.setText(self.account_data.get('imap_server', ''))
        layout.addRow("IMAP 服务器:", self.imap_server_edit)
        
        # IMAP 端口
        self.imap_port_edit = QLineEdit()
        self.imap_port_edit.setPlaceholderText("993")
        if self.account_data:
            self.imap_port_edit.setText(str(self.account_data.get('imap_port', 993)))
        layout.addRow("IMAP 端口:", self.imap_port_edit)
        
        # SMTP 服务器
        self.smtp_server_edit = QLineEdit()
        self.smtp_server_edit.setPlaceholderText("例如：smtp.gmail.com")
        if self.account_data:
            self.smtp_server_edit.setText(self.account_data.get('smtp_server', ''))
        layout.addRow("SMTP 服务器:", self.smtp_server_edit)
        
        # SMTP 端口
        self.smtp_port_edit = QLineEdit()
        self.smtp_port_edit.setPlaceholderText("587")
        if self.account_data:
            self.smtp_port_edit.setText(str(self.account_data.get('smtp_port', 587)))
        layout.addRow("SMTP 端口:", self.smtp_port_edit)
        
        # 使用 SSL
        self.use_ssl_check = QCheckBox("使用 SSL/TLS")
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


# ==================== API 接口方法 ====================

def get_account_config(account_name):
    """根据账号名称获取配置"""
    if not os.path.exists(CONFIG_FILE):
        raise ValueError(f"配置文件不存在：{CONFIG_FILE}")
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for acc in data.get("accounts", []):
        if acc.get("name") == account_name:
            return acc
    
    raise ValueError(f"未找到账号配置：{account_name}")


def get_recent_emails_api(account_name: str, limit: int=20):
    """
    API: 获取最近的邮件列表 - 直接调用 UI 的获取逻辑
    
    Args:
        account_name: 账号名称
        limit: int 获取邮件数量限制, 默认为20 建议少一点
    
    Returns:
        list: 邮件列表
    """
    # 这个方法不需要单独实现，由 UI 通过 EmailFetchWorker 异步获取
    # 如果需要同步版本供其他插件调用，可以这样实现：
    account_config = get_account_config(account_name)
    worker = EmailFetchWorker(account_config, limit)
    
    # 使用事件循环等待结果（不推荐在 GUI 线程中使用）
    import time
    error = []
    
    # def on_emails(emails):
    #     logger.info(f"Received {len(emails)} emails")
    #     result.extend(emails)
    
    def on_error(err):
        error.append(err)
    
    # worker.emails_fetched.connect(on_emails)
    worker.error_occurred.connect(on_error)
    worker.start()
    
    # 等待完成（最多 30 秒）
    timeout = 30
    start_time = time.time()
    while not worker.isFinished() and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if error:
        raise Exception(error[0])
    logger.info(worker.result)
    return worker.result


def get_email_detail_api(account_name, email_id):
    """
    API: 获取邮件详情
    
    Args:
        account_name: 账号名称
        email_id: 邮件 ID
    
    Returns:
        dict: 邮件详情
    """
    account_config = get_account_config(account_name)
    
    imap_server = account_config.get('imap_server')
    imap_port = account_config.get('imap_port', 993)
    username = account_config.get('username')
    password = account_config.get('password')
    use_ssl = account_config.get('use_ssl', True)
    
    # 连接 IMAP 服务器
    if use_ssl:
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    else:
        mail = imaplib.IMAP4(imap_server, imap_port)
    
    mail.login(username, password)
    mail.select('inbox')
    
    status, msg_data = mail.fetch(email_id.encode(), '(RFC822)')
    raw_email = msg_data[0][1]
    email_obj = email.message_from_bytes(raw_email)
    
    # 解码邮件头
    def decode_header_safe(header):
        decoded_parts = email.header.decode_header(header)
        decoded_str = ''
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    decoded_str += part.decode(encoding or 'utf-8', errors='replace')
                except:
                    decoded_str += part.decode('utf-8', errors='replace')
            else:
                decoded_str += part
        return decoded_str
    
    subject = decode_header_safe(email_obj.get('Subject', ''))
    from_str = decode_header_safe(email_obj.get('From', ''))
    to_str = decode_header_safe(email_obj.get('To', ''))
    
    date_str = email_obj.get('Date', '')
    try:
        date_obj = email.utils.parsedate_to_datetime(date_str)
        date_display = date_obj.strftime('%Y-%m-%d %H:%M')
    except:
        date_display = date_str
    
    # 提取正文
    body_plain = ''
    body_html = ''
    
    if email_obj.is_multipart():
        for part in email_obj.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            if content_type == 'text/plain' and 'attachment' not in content_disposition:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body_plain = payload.decode(charset, errors='replace')
                except:
                    pass
            elif content_type == 'text/html' and not body_html:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body_html = payload.decode(charset, errors='replace')
                except:
                    pass
    else:
        try:
            payload = email_obj.get_payload(decode=True)
            if payload:
                charset = email_obj.get_content_charset() or 'utf-8'
                body_plain = payload.decode(charset, errors='replace')
        except:
            pass
    
    # 提取附件
    attachments = []
    if email_obj.is_multipart():
        for part in email_obj.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get("Content-Disposition"):
                filename = part.get_filename()
                if filename:
                    attachments.append({
                        'filename': filename,
                        'size': len(part.get_payload(decode=True) or b''),
                        'content_type': part.get_content_type(),
                    })
    
    mail.close()
    mail.logout()
    
    return {
        'id': email_id,
        'subject': subject,
        'from': from_str,
        'to': to_str,
        'date': date_display,
        'body': body_plain,
        'body_html': body_html,
        'attachments': attachments,
    }


def send_email_api(account_name: str, to: str, subject: str, body: str, attachments: list[str]=None):
    """
    API: 发送邮件
    
    Args:
        bool: 发送是否成功
        account_name: 账号名称
        to: 收件人邮箱, 注意多个收件人用逗号","分隔
        subject: 邮件主题
        body: 邮件正文
        attachments: 附件文件路径列表
    
    Returns:
        bool: 发送是否成功
    """
    account_config = get_account_config(account_name)
    
    smtp_server = account_config.get('smtp_server')
    smtp_port = account_config.get('smtp_port', 587)
    username = account_config.get('username')
    password = account_config.get('password')
    use_ssl = account_config.get('use_ssl', True)
    
    # 创建邮件
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = username
    msg['To'] = to
    
    # 添加正文
    msg.attach(MIMEText(body, 'html', 'utf-8'))
    
    # 添加附件
    if attachments:
        for file_path in attachments:
            try:
                with open(file_path, 'rb') as f:
                    attachment = MIMEBase('application', 'octet-stream')
                    attachment.set_payload(f.read())
                    encoders.encode_base64(attachment)
                    
                    filename = os.path.basename(file_path)
                    attachment.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{filename}"'
                    )
                    msg.attach(attachment)
            except Exception as e:
                print(f"添加附件失败：{e}")
                raise
    
    # 发送邮件
    if use_ssl:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
    else:
        server = smtplib.SMTP(smtp_server, smtp_port)
    
    server.login(username, password)
    server.send_message(msg)
    server.quit()
    
    return True


def get_attachments_api(account_name, email_id):
    """API: 获取邮件附件列表"""
    detail = get_email_detail_api(account_name, email_id)
    return detail.get('attachments', [])


def download_attachment_api(account_name, email_id, filename, save_path):
    """API: 下载附件"""
    account_config = get_account_config(account_name)
    
    imap_server = account_config.get('imap_server')
    imap_port = account_config.get('imap_port', 993)
    username = account_config.get('username')
    password = account_config.get('password')
    use_ssl = account_config.get('use_ssl', True)
    
    # 连接 IMAP 服务器
    if use_ssl:
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    else:
        mail = imaplib.IMAP4(imap_server, imap_port)
    
    mail.login(username, password)
    mail.select('inbox')
    
    status, msg_data = mail.fetch(email_id.encode(), '(RFC822)')
    raw_email = msg_data[0][1]
    email_obj = email.message_from_bytes(raw_email)
    
    # 查找并下载附件
    if email_obj.is_multipart():
        for part in email_obj.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get("Content-Disposition"):
                part_filename = part.get_filename()
                if part_filename == filename:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            with open(save_path, 'wb') as f:
                                f.write(payload)
                            mail.close()
                            mail.logout()
                            return True
                    except Exception as e:
                        print(f"下载附件失败：{e}")
                        mail.close()
                        mail.logout()
                        return False
    
    mail.close()
    mail.logout()
    return False


def get_accounts_api():
    """API: 获取所有配置的邮箱账号"""
    if not os.path.exists(CONFIG_FILE):
        return []
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 不返回密码
    accounts = []
    for acc in data.get("accounts", []):
        safe_acc = acc.copy()
        safe_acc.pop('password', None)
        accounts.append(safe_acc)
    
    return accounts


# ==================== 插件入口函数 ====================

def load_plugin(plugin_manager):
    """
    插件加载入口函数
    
    Args:
        plugin_manager: 插件管理器实例
    
    Returns:
        dict: 包含插件组件的字典
    """
    print("[EmailUtils] 正在加载邮箱工具插件...")
    
    # 创建标签页实例
    email_tab = EmailManagerTab(plugin_manager=plugin_manager)
    
    # 注册暴露的方法到全局域
    plugin_manager.register_method(
        "email_utils", "get_recent_emails", get_recent_emails_api
    )
    plugin_manager.register_method(
        "email_utils", "get_email_detail", get_email_detail_api
    )
    plugin_manager.register_method(
        "email_utils", "send_email", send_email_api
    )
    plugin_manager.register_method(
        "email_utils", "get_attachments", get_attachments_api
    )
    plugin_manager.register_method(
        "email_utils", "download_attachment", download_attachment_api
    )
    plugin_manager.register_method(
        "email_utils", "get_accounts", get_accounts_api
    )
    
    # 添加到标签页
    plugin_manager.add_plugin_tab("email_utils", "📧 邮箱管理", email_tab, position=2)
    
    print("[EmailUtils] 邮箱工具插件加载完成")
    return {"tab": email_tab, "namespace": "email_utils"}


def unload_plugin(plugin_manager):
    """
    插件卸载回调
    
    Args:
        plugin_manager: 插件管理器实例
    """
    print("[EmailUtils] 正在卸载邮箱工具插件...")
    # 清理资源、保存状态等
    print("[EmailUtils] 邮箱工具插件卸载完成")
