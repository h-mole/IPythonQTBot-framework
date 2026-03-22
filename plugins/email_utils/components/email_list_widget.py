"""
邮箱工具插件 - 邮件列表组件
提供邮件列表显示、刷新和管理功能
"""

import os
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QMessageBox, QProgressBar, QMenu
)
from PySide6.QtCore import Qt, Signal, QThread
import logging

logger = logging.getLogger(__name__)


class EmailFetchWorker(QThread):
    """后台邮件拉取线程"""
    
    emails_fetched = Signal(list)  # 信号：邮件列表获取完成
    error_occurred = Signal(str)   # 信号：发生错误
    
    def __init__(self, account_config, limit=20):
        super().__init__()
        self.account_config = account_config
        self.limit = limit
        self.result = []
        
    def run(self):
        """线程运行方法"""
        try:
            from ..core.email_client import EmailClient
            from ..core.email_cache import EmailCacheManager
            
            client = EmailClient(self.account_config)
            username = self.account_config.get('username')
            
            # 连接服务器
            client.connect_imap()
            
            # 获取服务器上的邮件 ID 列表
            server_email_ids = client.fetch_email_ids(limit=self.limit)
            
            # 初始化缓存管理器
            cache_manager = EmailCacheManager(username)
            cached_ids = cache_manager.get_cached_email_ids()
            
            # 增量更新：只下载新邮件
            new_ids = set(server_email_ids) - cached_ids
            logger.info(f"发现 {len(new_ids)} 封新邮件")
            
            emails = []
            
            # 先加载缓存的邮件
            for email_id in server_email_ids:
                if email_id in cached_ids:
                    # 从缓存加载
                    try:
                        _, email_info = cache_manager.load_cached_email(email_id)
                        emails.append({
                            'id': email_info['id'],
                            'subject': email_info['subject'],
                            'from': email_info['from'],
                            'date': email_info['date'],
                            'preview': email_info['preview'],
                            'has_attachment': email_info['has_attachment'],
                        })
                    except Exception as e:
                        logger.warning(f"加载缓存邮件失败 {email_id}: {e}")
                        # 缓存损坏，重新从服务器获取
                        raw_data = client.fetch_email_raw(email_id)
                        email_info = cache_manager.save_email(email_id, raw_data)
                        emails.append(email_info)
                else:
                    # 新邮件，从服务器获取并缓存
                    try:
                        raw_data = client.fetch_email_raw(email_id)
                        email_info = cache_manager.save_email(email_id, raw_data)
                        emails.append(email_info)
                    except Exception as e:
                        logger.warning(f"获取新邮件失败 {email_id}: {e}")
                        continue
            
            # 断开连接
            client.disconnect_imap()
            
            logger.info(f"Fetched {len(emails)} emails")
            self.emails_fetched.emit(emails)
            self.result = emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}", exc_info=True)
            self.error_occurred.emit(str(e))


class EmailListWidget(QWidget):
    """邮件列表组件"""
    
    # 表格列定义
    COLUMNS = [
        "ID",
        "主题",
        "发件人",
        "日期",
        "预览",
        "附件",
    ]
    
    # 信号：邮件详情请求
    email_detail_requested = Signal(str)  # email_id
    
    def __init__(self, plugin_manager=None):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.config_file = None  # 由外部设置
        self.emails_data = []
        self.current_account = None
        self.fetch_worker = None
        
        # 加载配置
        self.accounts_config = []
        self._load_accounts_config()
        
        self.init_ui()
        
        # 如果有配置的账号，自动选择第一个
        if self.accounts_config:
            self.account_combo.setCurrentIndex(0)
            self.on_account_changed()
    
    def _load_accounts_config(self):
        """加载账号配置"""
        from ..utils.helpers import load_accounts_config
        self.accounts_config = load_accounts_config()
    
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
        
        # 添加右键菜单支持
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
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
    
    def on_account_changed(self):
        """账号改变时的处理"""
        account_name = self.account_combo.currentText()
        self.current_account = account_name
        
        # 自动刷新邮件
        self.fetch_emails()
    
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
        """查看邮件详情"""
        if row >= len(self.emails_data):
            return
        
        email_data = self.emails_data[row]
        email_id = email_data.get('id')
        
        if not email_id:
            logger.warning(f"警告：邮件 ID 为空，无法查看详情！")
            return
        
        # 发射信号，由父组件处理
        self.email_detail_requested.emit(email_id)
    
    def show_context_menu(self, pos):
        """显示右键菜单"""
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        
        menu = QMenu(self)
        
        view_action = menu.addAction("查看邮件详情")
        view_action.triggered.connect(lambda: self.view_email_detail(row, 0))
        
        refresh_action = menu.addAction("刷新此邮件")
        refresh_action.triggered.connect(lambda: self.refresh_single_email(row))
        
        menu.exec_(self.table.viewport().mapToGlobal(pos))
    
    def refresh_single_email(self, row):
        """刷新单封邮件"""
        if row >= len(self.emails_data):
            return
        
        email_data = self.emails_data[row]
        email_id = email_data.get('id')
        
        if not email_id:
            return
        
        # TODO: 实现单封邮件的刷新逻辑
        QMessageBox.information(self, "提示", f"刷新邮件 {email_id}")
    
    def compose_email(self):
        """撰写新邮件"""
        if not self.current_account:
            QMessageBox.warning(self, "警告", "请先选择邮箱账号！")
            return
        
        # 使用信号通知父组件
        from .send_email_dialog import SendEmailDialog
        dialog = SendEmailDialog(self.parent(), self.current_account)
        dialog.exec()
    
    def show_account_config(self):
        """显示账号配置对话框"""
        from .account_config_dialog import AccountConfigDialog
        from ..utils.helpers import save_accounts_config
        
        dialog = AccountConfigDialog(self.parent(), self.accounts_config)
        if dialog.exec() == int(QDialog.DialogCode.Accepted):
            self.accounts_config = dialog.accounts_config
            save_accounts_config(self.accounts_config)
            self.update_account_combo()
