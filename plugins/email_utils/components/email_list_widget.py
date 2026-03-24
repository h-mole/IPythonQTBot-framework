"""
邮箱工具插件 - 邮件列表组件
使用 QTableView + 自定义 Model 提供高性能邮件列表显示
"""

import os
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QTableView, QHeaderView, QMessageBox, QProgressBar, QMenu,
    QLineEdit, QComboBox
)
from PySide6.QtCore import Qt, Signal, QThread, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
import logging

logger = logging.getLogger(__name__)


def clean_preview_text(text: str) -> str:
    """
    清理预览文本：
    1. 如果以 <html> 开头，解析提取纯文本
    2. 去掉开头的换行符，变为空格在同一行显示
    """
    if not text:
        return ""
    
    # 检查是否以 <html> 开头（不区分大小写，去除前导空白）
    text_stripped = text.lstrip()
    if text_stripped.lower().startswith('<html>'):
        # 使用 HTML 解析器提取文本
        try:
            from html.parser import HTMLParser
            
            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.texts = []
                    self.in_style = False
                    self.in_script = False
                
                def handle_starttag(self, tag, attrs):
                    if tag.lower() in ('style', 'script'):
                        if tag.lower() == 'style':
                            self.in_style = True
                        else:
                            self.in_script = True
                
                def handle_endtag(self, tag):
                    if tag.lower() == 'style':
                        self.in_style = False
                    elif tag.lower() == 'script':
                        self.in_script = False
                
                def handle_data(self, data):
                    if not self.in_style and not self.in_script:
                        self.texts.append(data)
                
                def get_text(self):
                    return ' '.join(self.texts)
            
            parser = TextExtractor()
            parser.feed(text)
            text = parser.get_text()
        except Exception:
            # 解析失败则使用原始文本
            pass
    
    # 处理开头换行符 - 将开头的所有空白字符（包括换行、空格、制表符）替换为单个空格
    # 找到第一个非空白字符的位置
    result = text.lstrip()
    if len(result) < len(text):
        # 说明前面有空白字符，替换为一个空格
        result = ' ' + result
    
    # 将文本中的所有换行符替换为空格，确保在一行显示
    result = result.replace('\n', ' ').replace('\r', ' ')
    
    # 合并多个连续空格为一个
    while '  ' in result:
        result = result.replace('  ', ' ')
    
    # 限制长度
    if len(result) > 200:
        result = result[:200] + '...'
    
    return result.strip()


class EmailTableModel(QAbstractTableModel):
    """邮件列表数据模型 - 高性能处理大量数据"""
    
    COLUMNS = [
        ("账号", 80),
        ("主题", 250),
        ("发件人", 300),
        ("日期", 120),
        ("预览", 350),
        ("附件", 50),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []  # 全部邮件数据
        self._filtered_data = []  # 筛选后的数据
        self._filter_text = ""
        self._account_name_map = {}  # 邮箱地址 -> 账号名称 的映射
    
    def rowCount(self, parent=QModelIndex()):
        return len(self._filtered_data)
    
    def columnCount(self, parent=QModelIndex()):
        return len(self.COLUMNS)
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._filtered_data):
            return None
        
        email = self._filtered_data[index.row()]
        col = index.column()
        
        if role == Qt.DisplayRole:
            if col == 0:  # 账号 - 显示配置中的账号名称
                account = email.get('account', '')
                return self._get_account_display_name(account)
            elif col == 1:  # 主题
                return email.get('subject', '')
            elif col == 2:  # 发件人
                return email.get('from', '')
            elif col == 3:  # 日期
                return email.get('date', '')
            elif col == 4:  # 预览（清理后的文本）
                preview = email.get('preview', '')
                return clean_preview_text(preview)
            elif col == 5:  # 附件
                return "📎" if email.get('has_attachment') else ""
            return ""
        
        elif role == Qt.ToolTipRole:
            if col == 1:  # 主题提示
                return email.get('subject', '')
            elif col == 4:  # 预览提示（显示原始预览内容）
                return email.get('preview', '')
            elif col == 0:  # 账号提示显示完整邮箱和名称
                account = email.get('account', '')
                name = self._get_account_display_name(account)
                if name != account:
                    return f"{name} ({account})"
                return account
        
        elif role == Qt.TextAlignmentRole:
            if col == 5:  # 附件列居中
                return Qt.AlignCenter
            return Qt.AlignLeft | Qt.AlignVCenter
        
        elif role == Qt.UserRole:  # 返回完整数据
            return email
        
        return None
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.COLUMNS[section][0]
        return None
    
    def _get_account_display_name(self, account: str) -> str:
        """获取账号的显示名称 - 使用配置中的名称"""
        if not account:
            return ""
        # 优先使用映射中的名称
        if account in self._account_name_map:
            return self._account_name_map[account]
        # 如果没有映射，显示邮箱前缀
        if '@' in account:
            return account.split('@')[0]
        return account[:15]
    
    def set_account_name_map(self, name_map: dict):
        """设置邮箱地址到账号名称的映射"""
        self._account_name_map = name_map
        # 刷新显示
        self.beginResetModel()
        self.endResetModel()
    
    def set_data(self, emails):
        """设置全部数据并按日期倒序排序"""
        self.beginResetModel()
        # 按日期倒序排序
        self._data = sorted(emails, key=self._sort_key, reverse=True)
        self._apply_filter()
        self.endResetModel()
    
    def add_emails(self, emails):
        """添加邮件（用于增量加载）"""
        if not emails:
            return
        
        # 去重添加
        existing_ids = {e.get('id') for e in self._data}
        new_emails = [e for e in emails if e.get('id') not in existing_ids]
        
        if new_emails:
            self.beginResetModel()
            self._data.extend(new_emails)
            # 按日期排序
            self._data.sort(key=self._sort_key, reverse=True)
            self._apply_filter()
            self.endResetModel()
    
    def clear(self):
        """清空数据"""
        self.beginResetModel()
        self._data = []
        self._filtered_data = []
        self.endResetModel()
    
    def set_filter(self, text: str):
        """设置搜索筛选"""
        self.beginResetModel()
        self._filter_text = text.lower()
        self._apply_filter()
        self.endResetModel()
    
    def _apply_filter(self):
        """应用筛选"""
        if not self._filter_text:
            self._filtered_data = self._data.copy()
        else:
            self._filtered_data = [
                e for e in self._data
                if (self._filter_text in e.get('subject', '').lower() or
                    self._filter_text in e.get('from', '').lower() or
                    self._filter_text in e.get('preview', '').lower() or
                    self._filter_text in e.get('account', '').lower())
            ]
    
    def _sort_key(self, email):
        """排序键 - 解析邮件日期用于排序"""
        date_str = email.get('date', '')
        if not date_str:
            return datetime.min
        
        # 尝试多种日期格式
        date_formats = [
            '%Y-%m-%d %H:%M:%S',      # 2024-03-22 14:30:00
            '%Y-%m-%d %H:%M',         # 2024-03-22 14:30
            '%Y-%m-%d',               # 2024-03-22
            '%d %b %Y %H:%M:%S',      # 22 Mar 2024 14:30:00
            '%d %b %Y %H:%M',         # 22 Mar 2024 14:30
            '%d %b %Y',               # 22 Mar 2024
            '%a, %d %b %Y %H:%M:%S',  # Mon, 22 Mar 2024 14:30:00 (RFC 2822)
        ]
        
        # 先尝试 email.utils 解析标准邮件格式
        try:
            import email.utils
            parsed = email.utils.parsedate_to_datetime(date_str)
            if parsed.tzinfo is not None:
                parsed = parsed.replace(tzinfo=None)
            return parsed
        except:
            pass
        
        # 尝试其他格式
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
        
        # 都失败了，返回最小时间
        logger.debug(f"无法解析日期: {date_str}")
        return datetime.min
    
    def get_email_at(self, row):
        """获取指定行的邮件数据"""
        if 0 <= row < len(self._filtered_data):
            return self._filtered_data[row]
        return None
    
    def get_all_emails(self):
        """获取所有邮件（用于筛选等操作）"""
        return self._data


class EmailFetchWorker(QThread):
    """后台邮件拉取线程 - 支持多账号"""
    
    emails_fetched = Signal(list)  # 信号：邮件列表获取完成
    email_found = Signal(dict)     # 信号：发现单封新邮件（实时更新用）
    account_progress = Signal(str, int, int)  # 信号：账号进度更新（账号名, 当前, 总数）
    account_finished = Signal(str, int, bool, str)  # 信号：单个账号完成（账号名, 数量, 是否成功, 错误信息）
    error_occurred = Signal(str)   # 信号：发生错误
    progress_updated = Signal(int, int)  # 信号：进度更新（当前数量，总数）
    fetch_finished = Signal()      # 信号：拉取完成（用于重置状态）
    
    def __init__(self, accounts_config, mode='incremental', days=None):
        super().__init__()
        self.accounts_config = accounts_config  # 可以是单个配置或配置列表
        self.mode = mode  # 'incremental', 'history', 'cached_days'
        self.days = days
        self.result = []
        self._is_running = True
        
    def stop(self):
        """停止线程"""
        self._is_running = False
        self.wait(1000)
        
    def run(self):
        """线程运行方法 - 轮流拉取所有账号"""
        # 统一转换为列表
        if isinstance(self.accounts_config, dict):
            accounts = [self.accounts_config]
        else:
            accounts = self.accounts_config or []
        
        if not accounts:
            self.error_occurred.emit("没有配置账号")
            self.fetch_finished.emit()
            return
        
        all_emails = []
        total_accounts = len(accounts)
        
        for idx, account_config in enumerate(accounts):
            if not self._is_running:
                break
                
            account_name = account_config.get('name', f'账号{idx+1}')
            username = account_config.get('username', '')
            
            try:
                logger.info(f"[{account_name}] 开始拉取邮件...")
                self.account_progress.emit(account_name, idx + 1, total_accounts)
                
                account_emails = self._fetch_single_account(account_config)
                
                if account_emails:
                    all_emails.extend(account_emails)
                    logger.info(f"[{account_name}] 成功拉取 {len(account_emails)} 封邮件")
                    self.account_finished.emit(account_name, len(account_emails), True, "")
                else:
                    logger.info(f"[{account_name}] 没有新邮件")
                    self.account_finished.emit(account_name, 0, True, "")
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[{account_name}] 拉取失败: {error_msg}", exc_info=True)
                self.account_finished.emit(account_name, 0, False, error_msg)
                # 继续处理下一个账号，不中断
        
        if self._is_running:
            # 按日期排序
            all_emails.sort(key=self._sort_key, reverse=True)
            logger.info(f"所有账号共拉取 {len(all_emails)} 封邮件")
            self.emails_fetched.emit(all_emails)
            self.result = all_emails
        
        self.fetch_finished.emit()
    
    def _fetch_single_account(self, account_config):
        """拉取单个账号的邮件"""
        account_name = account_config.get('name')
        
        if self.mode == 'incremental':
            from ..api.email_api import get_incremental_emails_api
            return get_incremental_emails_api(
                account_name=account_name,
                batch_size=10
            )
        elif self.mode == 'cached_days':
            from ..api.email_api import get_cached_emails_by_days_api
            return get_cached_emails_by_days_api(
                account_name=account_name,
                days=self.days
            )
        else:
            from ..api.email_api import get_recent_emails_with_history_api
            # 注意：历史模式不支持实时回调多账号
            return get_recent_emails_with_history_api(
                account_name=account_name,
                limit=20,
                days=self.days,
                progress_callback=None
            )
    
    def _sort_key(self, email):
        """排序键 - 解析邮件日期用于排序"""
        date_str = email.get('date', '')
        if not date_str:
            return datetime.min
        
        # 尝试多种日期格式
        date_formats = [
            '%Y-%m-%d %H:%M:%S',      # 2024-03-22 14:30:00
            '%Y-%m-%d %H:%M',         # 2024-03-22 14:30
            '%Y-%m-%d',               # 2024-03-22
            '%d %b %Y %H:%M:%S',      # 22 Mar 2024 14:30:00
            '%d %b %Y %H:%M',         # 22 Mar 2024 14:30
            '%d %b %Y',               # 22 Mar 2024
            '%a, %d %b %Y %H:%M:%S',  # Mon, 22 Mar 2024 14:30:00 (RFC 2822)
        ]
        
        # 先尝试 email.utils 解析标准邮件格式
        try:
            import email.utils
            parsed = email.utils.parsedate_to_datetime(date_str)
            if parsed.tzinfo is not None:
                parsed = parsed.replace(tzinfo=None)
            return parsed
        except:
            pass
        
        # 尝试其他格式
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
        
        # 都失败了，返回最小时间
        return datetime.min
    
    def _on_new_email_found(self, email_info, current_count, total_new):
        """新邮件发现回调"""
        if self._is_running:
            self.email_found.emit(email_info)
            self.progress_updated.emit(current_count, total_new)


class EmailListWidget(QWidget):
    """邮件列表组件"""
    
    # 信号：邮件详情请求
    email_detail_requested = Signal(str, str)  # email_id, account_name
    
    def __init__(self, plugin_manager=None):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.config_file = None  # 由外部设置
        self.fetch_worker = None
        self.is_fetching = False  # 防重复刷新标志
        self._first_load_done = False  # 首次加载完成标志
        
        # 加载配置
        self.accounts_config = []
        self._load_accounts_config()
        
        # 当前操作的账号（用于写邮件、回复邮件等）
        self.current_account = None
        if self.accounts_config:
            self.current_account = self.accounts_config[0].get('name')
        
        self.init_ui()
        
        # 初始化账号名称映射
        self._update_account_name_map()
        
        # 自动刷新邮件（首次加载）- 拉取所有账号
        if self.accounts_config:
            self.fetch_emails_with_cache_check()
    
    def _load_accounts_config(self):
        """加载账号配置"""
        from ..utils.helpers import load_accounts_config
        self.accounts_config = load_accounts_config()
        # 更新账号名称映射（邮箱地址 -> 账号名称）
        self._update_account_name_map()
    
    def _update_account_name_map(self):
        """更新邮箱地址到账号名称的映射"""
        name_map = {}
        for acc in self.accounts_config:
            # username 是邮箱地址，name 是用户自定义的账号名称
            username = acc.get('username', '')
            name = acc.get('name', '')
            if username and name:
                name_map[username] = name
                # 同时把 name 也映射到自身（用于邮件数据中 account 字段是 name 的情况）
                name_map[name] = name
        # 设置到模型
        if hasattr(self, 'email_model'):
            self.email_model.set_account_name_map(name_map)
    
    def _get_account_name_for_email(self, account_identifier):
        """
        根据账号标识（邮箱地址或名称）获取账号名称
        
        Args:
            account_identifier: 邮箱地址或账号名称
            
        Returns:
            str: 账号名称，找不到返回None
        """
        if not account_identifier:
            return None
        
        # 直接匹配账号名称
        for acc in self.accounts_config:
            if acc.get('name') == account_identifier:
                return acc.get('name')
        
        # 匹配邮箱地址
        for acc in self.accounts_config:
            if acc.get('username') == account_identifier:
                return acc.get('name')
        
        return None
    
    def init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        self.setLayout(main_layout)
        
        # 顶部控制区域
        control_frame = QFrame()
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)
        control_frame.setLayout(control_layout)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("🔄 刷新邮件")
        self.refresh_btn.setToolTip("拉取最新邮件（如果前10封中有已缓存的，会自动加载60天内的缓存）")
        self.refresh_btn.clicked.connect(self.fetch_emails_with_cache_check)
        control_layout.addWidget(self.refresh_btn)
        
        # 拉取历史邮件按钮
        self.history_btn = QPushButton("📜 拉取历史")
        self.history_btn.clicked.connect(self.fetch_history_emails)
        control_layout.addWidget(self.history_btn)
        
        # 写邮件按钮
        self.compose_btn = QPushButton("📝 写邮件")
        self.compose_btn.clicked.connect(self.compose_email)
        control_layout.addWidget(self.compose_btn)
        
        # 账号配置按钮
        self.config_btn = QPushButton("⚙️ 账号配置")
        self.config_btn.clicked.connect(self.show_account_config)
        control_layout.addWidget(self.config_btn)
        
        control_layout.addStretch()
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.setSpacing(5)
        search_layout.addWidget(QLabel("🔍"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索主题、发件人、内容... (按Enter)")
        self.search_edit.setMinimumWidth(220)
        # 按 Enter 触发搜索，避免输入时卡顿
        self.search_edit.returnPressed.connect(self.on_search_triggered)
        self.search_edit.setClearButtonEnabled(True)
        search_layout.addWidget(self.search_edit)
        
        # 清空搜索按钮
        self.clear_search_btn = QPushButton("清空")
        self.clear_search_btn.setFixedWidth(50)
        self.clear_search_btn.setToolTip("清空搜索条件")
        self.clear_search_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(self.clear_search_btn)
        
        control_layout.addLayout(search_layout)
        
        # 账号筛选（下拉框）
        control_layout.addWidget(QLabel("筛选:"))
        self.filter_combo = QComboBox()
        self.filter_combo.setMinimumWidth(100)
        self.filter_combo.addItem("全部账号")
        self.filter_combo.currentTextChanged.connect(self.on_filter_changed)
        control_layout.addWidget(self.filter_combo)
        
        main_layout.addWidget(control_frame)
        
        # 邮件列表 - 使用 QTableView + 自定义 Model
        self.table = QTableView()
        self.email_model = EmailTableModel(self)
        self.table.setModel(self.email_model)
        
        # 设置表格属性
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setMouseTracking(True)
        
        # 设置列宽
        header = self.table.horizontalHeader()
        for i, (name, width) in enumerate(self.email_model.COLUMNS):
            if width > 0:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                self.table.setColumnWidth(i, width)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        
        # 主题和预览列可以拉伸
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 主题
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # 预览
        
        # 连接双击信号
        self.table.doubleClicked.connect(self.view_email_detail)
        
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
        
        # 更新筛选下拉框
        self.update_filter_combo()
    
    def update_filter_combo(self):
        """更新账号筛选框"""
        current_filter = self.filter_combo.currentText()
        
        self.filter_combo.clear()
        self.filter_combo.addItem("全部账号")
        
        for account in self.accounts_config:
            name = account.get('name', '')  # 用户自定义的账号名称
            if name:
                # 显示账号名称
                self.filter_combo.addItem(name)
        
        # 尝试恢复之前的选择
        if current_filter:
            index = self.filter_combo.findText(current_filter)
            if index >= 0:
                self.filter_combo.setCurrentIndex(index)
    
    def on_search_triggered(self):
        """按 Enter 触发搜索"""
        search_text = self.search_edit.text().strip()
        self.email_model.set_filter(search_text)
        self._update_status_label()
        
        # 更新状态提示
        if search_text:
            self.status_label.setText(f"搜索: '{search_text}' | 找到 {self.email_model.rowCount()} 封邮件")
    
    def clear_search(self):
        """清空搜索"""
        self.search_edit.clear()
        self.email_model.set_filter("")
        self._update_status_label()
    
    def on_filter_changed(self):
        """筛选条件改变时的处理"""
        # 获取当前选中的账号名称
        display_name = self.filter_combo.currentText()
        
        if not display_name or display_name == "全部账号":
            # 显示全部
            all_emails = self.email_model.get_all_emails()
            self.email_model.set_data(all_emails)
        else:
            # 按账号筛选 - 需要匹配账号名称或邮箱地址
            # 获取该显示名称对应的邮箱地址
            target_accounts = set()
            for acc in self.accounts_config:
                if acc.get('name') == display_name:
                    target_accounts.add(acc.get('username', ''))
                    target_accounts.add(acc.get('name', ''))
            
            # 筛选邮件
            all_emails = self.email_model.get_all_emails()
            filtered = [e for e in all_emails if e.get('account') in target_accounts]
            self.email_model.set_data(filtered)
        
        self._update_status_label()
    
    def _update_status_label(self):
        """更新状态标签"""
        total = len(self.email_model.get_all_emails())
        filtered = self.email_model.rowCount()
        
        if filtered != total:
            self.status_label.setText(f"显示 {filtered} / 共 {total} 封邮件")
        else:
            self.status_label.setText(f"共 {total} 封邮件")
    
    def fetch_emails_with_cache_check(self):
        """
        获取邮件（带缓存检查的智能刷新）- 拉取所有账号
        对于前10个邮件中，如果已经有缓存的了，就把60天内所有的缓存的邮件也一起加载
        """
        # 防重复刷新检查
        if self.is_fetching:
            logger.info("正在刷新中，忽略重复请求")
            return
        
        # 检查是否有配置的账号
        if not self.accounts_config or len(self.accounts_config) == 0:
            logger.warning("警告：请先配置邮箱账号，才能拉取！")
            QMessageBox.warning(self, "警告", "请先配置邮箱账号！")
            return
        
        # 停止之前的工作线程
        if self.fetch_worker and self.fetch_worker.isRunning():
            self.fetch_worker.stop()
        
        # 设置刷新状态
        self.is_fetching = True
        self.refresh_btn.setEnabled(False)
        self.history_btn.setEnabled(False)
        
        # 显示进度
        self.status_label.setText(f"正在获取 {len(self.accounts_config)} 个账号的邮件...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        
        # 清空现有数据
        self.email_model.clear()
        
        # 创建后台线程获取邮件（传入所有账号配置）
        self.fetch_worker = EmailFetchWorker(
            self.accounts_config, 
            mode='incremental'
        )
        self.fetch_worker.emails_fetched.connect(self.on_emails_fetched)
        self.fetch_worker.account_progress.connect(self.on_account_progress)
        self.fetch_worker.account_finished.connect(self.on_account_finished)
        self.fetch_worker.error_occurred.connect(self.on_fetch_error)
        self.fetch_worker.fetch_finished.connect(self.on_fetch_finished)
        self.fetch_worker.start()
    
    def fetch_history_emails(self):
        """拉取历史邮件（弹出对话框）- 所有账号"""
        # 防重复刷新检查
        if self.is_fetching:
            QMessageBox.information(self, "提示", "正在刷新中，请稍后再试")
            return
        
        # 检查是否有配置的账号
        if not self.accounts_config or len(self.accounts_config) == 0:
            QMessageBox.warning(self, "警告", "请先配置邮箱账号！")
            return
        
        # 显示历史邮件拉取对话框
        from .fetch_history_dialog import FetchHistoryDialog
        dialog = FetchHistoryDialog(self, default_days=60)
        
        if dialog.exec() != int(QDialog.DialogCode.Accepted):
            return
        
        days = dialog.get_days()
        if not days or days < 1:
            return
        
        # 停止之前的工作线程
        if self.fetch_worker and self.fetch_worker.isRunning():
            self.fetch_worker.stop()
        
        # 设置刷新状态
        self.is_fetching = True
        self.refresh_btn.setEnabled(False)
        self.history_btn.setEnabled(False)
        
        # 显示进度
        self.status_label.setText(f"正在拉取 {len(self.accounts_config)} 个账号最近 {days} 天的历史邮件...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        # 清空现有数据
        self.email_model.clear()
        
        # 创建后台线程获取邮件（所有账号）
        self.fetch_worker = EmailFetchWorker(
            self.accounts_config, 
            mode='history',
            days=days
        )
        self.fetch_worker.emails_fetched.connect(self.on_emails_fetched)
        self.fetch_worker.account_progress.connect(self.on_account_progress)
        self.fetch_worker.account_finished.connect(self.on_account_finished)
        self.fetch_worker.error_occurred.connect(self.on_fetch_error)
        self.fetch_worker.fetch_finished.connect(self.on_fetch_finished)
        self.fetch_worker.start()
    
    def load_cached_emails(self, days=60):
        """加载指定天数内的缓存邮件 - 所有账号"""
        if not self.accounts_config:
            return
        
        # 停止之前的工作线程
        if self.fetch_worker and self.fetch_worker.isRunning():
            self.fetch_worker.stop()
        
        # 设置状态
        self.is_fetching = True
        self.refresh_btn.setEnabled(False)
        self.history_btn.setEnabled(False)
        
        self.status_label.setText(f"正在加载 {len(self.accounts_config)} 个账号 {days} 天内的缓存邮件...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        # 创建后台线程获取缓存邮件（所有账号）
        self.fetch_worker = EmailFetchWorker(
            self.accounts_config, 
            mode='cached_days',
            days=days
        )
        self.fetch_worker.emails_fetched.connect(self.on_cached_emails_loaded)
        self.fetch_worker.account_progress.connect(self.on_account_progress)
        self.fetch_worker.account_finished.connect(self.on_account_finished)
        self.fetch_worker.error_occurred.connect(self.on_fetch_error)
        self.fetch_worker.fetch_finished.connect(self.on_fetch_finished)
        self.fetch_worker.start()
    
    def on_cached_emails_loaded(self, emails):
        """缓存邮件加载完成的回调"""
        if emails:
            self.email_model.add_emails(emails)
        self._update_status_label()
    
    def on_account_progress(self, account_name, current, total):
        """单个账号进度更新"""
        self.status_label.setText(f"正在拉取 [{account_name}]... ({current}/{total})")
    
    def on_account_finished(self, account_name, count, success, error_msg):
        """单个账号拉取完成"""
        if success:
            if count > 0:
                logger.info(f"[{account_name}] 拉取完成: {count} 封邮件")
            else:
                logger.info(f"[{account_name}] 拉取完成: 无新邮件")
        else:
            logger.warning(f"[{account_name}] 拉取失败: {error_msg}")
            # 显示在状态栏但不中断其他账号
            self.status_label.setText(f"[{account_name}] 失败: {error_msg[:30]}...")
    
    def on_email_found_realtime(self, email_info):
        """
        实时处理新发现的邮件
        """
        # 添加到模型
        self.email_model.add_emails([email_info])
        self._update_status_label()
    
    def on_progress_updated(self, current_count, total_new):
        """进度更新回调"""
        self.status_label.setText(f"已获取 {current_count}/{total_new} 封新邮件")
    
    def on_emails_fetched(self, emails):
        """邮件获取完成的回调"""
        # 检查是否需要加载历史缓存邮件（按账号分别检查）
        accounts_to_load_cache = set()
        
        if emails and len(emails) > 0:
            from ..core.email_cache import EmailCacheManager
            
            # 按账号分组检查前10封邮件
            account_emails = {}
            for email in emails:
                acc = email.get('account', '')
                if acc not in account_emails:
                    account_emails[acc] = []
                if len(account_emails[acc]) < 10:
                    account_emails[acc].append(email)
            
            # 对每个账号检查缓存状态
            for account_name, acc_emails in account_emails.items():
                try:
                    # 找到账号配置
                    account_config = None
                    for acc in self.accounts_config:
                        if acc.get('name') == account_name or acc.get('username') == account_name:
                            account_config = acc
                            break
                    
                    if not account_config:
                        continue
                    
                    username = account_config.get('username')
                    cache_manager = EmailCacheManager(username)
                    
                    # 检查前10封中是否有已缓存的
                    cached_count = 0
                    for email in acc_emails:
                        if cache_manager.is_email_cached(email.get('id')):
                            cached_count += 1
                    
                    # 如果该账号前10封中有缓存的，需要加载该账号的历史缓存
                    if cached_count > 0:
                        accounts_to_load_cache.add(account_name)
                        logger.info(f"[{account_name}] 前10封中有 {cached_count} 封已缓存，将加载其60天内的缓存")
                        
                except Exception as e:
                    logger.warning(f"检查 [{account_name}] 缓存状态失败：{e}")
        
        # 设置数据
        self.email_model.set_data(emails)
        self._update_status_label()
        
        # 如果需要，加载相关账号的历史缓存邮件
        if accounts_to_load_cache:
            logger.info(f"将为以下账号加载历史缓存: {accounts_to_load_cache}")
            # 直接调用加载缓存的方法，它会加载所有账号的缓存
            self.load_cached_emails(days=60)
    
    def on_fetch_error(self, error_msg):
        """获取邮件错误的回调"""
        self.status_label.setText("获取失败")
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "错误", f"获取邮件失败：{error_msg}")
    
    def on_fetch_finished(self):
        """拉取完成的回调（无论成功或失败）"""
        self.is_fetching = False
        self.refresh_btn.setEnabled(True)
        self.history_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self._update_status_label()
    
    def view_email_detail(self, index):
        """查看邮件详情"""
        if not index.isValid():
            return
        
        email_data = self.email_model.get_email_at(index.row())
        if not email_data:
            return
        
        email_id = email_data.get('id')
        if not email_id:
            logger.warning(f"警告：邮件 ID 为空，无法查看详情！")
            return
        
        # 获取邮件所属的账号名称
        # 先尝试从映射中查找，否则使用当前账号
        account_identifier = email_data.get('account', '')
        account_name = self._get_account_name_for_email(account_identifier)
        if not account_name:
            account_name = self.current_account
        
        # 发射信号，由父组件处理
        self.email_detail_requested.emit(email_id, account_name)
    
    def show_context_menu(self, pos):
        """显示右键菜单"""
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        
        row = index.row()
        email_data = self.email_model.get_email_at(row)
        if not email_data:
            return
        
        menu = QMenu(self)
        
        view_action = menu.addAction("查看邮件详情")
        view_action.triggered.connect(lambda: self.view_email_detail(index))
        
        # 添加回复邮件选项
        reply_action = menu.addAction("📧 回复邮件")
        reply_action.triggered.connect(lambda: self.reply_email(row))
        
        menu.addSeparator()
        
        refresh_action = menu.addAction("刷新此邮件")
        refresh_action.triggered.connect(lambda: self.refresh_single_email(row))
        
        menu.exec_(self.table.viewport().mapToGlobal(pos))
    
    def refresh_single_email(self, row):
        """刷新单封邮件"""
        email_data = self.email_model.get_email_at(row)
        if not email_data:
            return
        
        email_id = email_data.get('id')
        if not email_id:
            return
        
        # TODO: 实现单封邮件的刷新逻辑
        QMessageBox.information(self, "提示", f"刷新邮件 {email_id}")
    
    def compose_email(self):
        """撰写新邮件"""
        if not self.current_account:
            QMessageBox.warning(self, "警告", "请先配置邮箱账号！")
            return
        
        # 使用信号通知父组件
        from .send_email_dialog import SendEmailDialog
        dialog = SendEmailDialog(self.parent(), self.current_account)
        dialog.exec()
    
    def reply_email(self, row):
        """
        回复邮件
        
        Args:
            row: 邮件在表格中的行号
        """
        if not self.current_account:
            QMessageBox.warning(self, "警告", "请先配置邮箱账号！")
            return
        
        email_data = self.email_model.get_email_at(row)
        if not email_data:
            return
        
        email_id = email_data.get('id')
        if not email_id:
            QMessageBox.warning(self, "警告", "无法获取邮件ID！")
            return
        
        # 获取邮件详情以获取完整信息
        from ..api.email_api import get_email_detail_api
        
        try:
            detail = get_email_detail_api(self.current_account, email_id)
            
            # 构建回复正文（引用原文）
            original_body = detail.get('body', '')
            original_date = detail.get('date', '')
            original_from = detail.get('from', '')
            original_subject = detail.get('subject', '')
            
            # 创建引用格式的 HTML
            quoted_body = f"""
<div style="margin-top: 20px; border-top: 1px solid #ccc; padding-top: 10px; color: #666;">
    <div style="margin-bottom: 10px;">-------- 原始邮件 --------</div>
    <div><b>发件人:</b> {original_from}</div>
    <div><b>日期:</b> {original_date}</div>
    <div><b>主题:</b> {original_subject}</div>
    <br>
    <div>{original_body}</div>
</div>
"""
            
            # 构建完整正文（空回复区 + 引用）
            full_body = f"""
<div style="font-family: Arial, sans-serif;">
    <p><br></p>
    {quoted_body}
</div>
"""
            
            # 打开回复对话框
            from .send_email_dialog import SendEmailDialog
            dialog = SendEmailDialog(
                parent=self.parent(),
                account_name=self.current_account,
                reply_mode=True,
                reply_to_email=original_from,
                reply_subject=original_subject,
                reply_body=full_body
            )
            dialog.exec()
            
        except Exception as e:
            logger.error(f"获取邮件详情失败：{e}")
            QMessageBox.critical(self, "错误", f"获取邮件详情失败：{str(e)}")
    
    def show_account_config(self):
        """显示账号配置对话框"""
        from .account_config_dialog import AccountConfigDialog
        from ..utils.helpers import save_accounts_config
        
        dialog = AccountConfigDialog(self.parent(), self.accounts_config)
        if dialog.exec() == int(QDialog.DialogCode.Accepted):
            self.accounts_config = dialog.accounts_config
            save_accounts_config(self.accounts_config)
            
            # 更新当前账号和筛选框
            if self.accounts_config:
                self.current_account = self.accounts_config[0].get('name')
            self.update_filter_combo()
            
            # 更新账号名称映射
            self._update_account_name_map()
            
            # 重新加载邮件
            self.fetch_emails_with_cache_check()
    
    def closeEvent(self, event):
        """关闭事件处理"""
        # 确保工作线程被正确停止
        if self.fetch_worker and self.fetch_worker.isRunning():
            self.fetch_worker.stop()
        event.accept()
