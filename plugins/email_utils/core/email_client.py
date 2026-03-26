"""
邮箱工具插件 - 邮件客户端
封装 IMAP/SMTP 协议操作
"""

import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import logging

logger = logging.getLogger(__name__)


class EmailClient:
    """邮件客户端 - 封装 IMAP/SMTP 连接和操作"""
    
    def __init__(self, account_config):
        """
        初始化邮件客户端
        
        Args:
            account_config: 账号配置字典
        """
        self.config = account_config
        self.imap_server = account_config.get('imap_server')
        self.imap_port = account_config.get('imap_port', 993)
        self.smtp_server = account_config.get('smtp_server')
        self.smtp_port = account_config.get('smtp_port', 587)
        self.username = account_config.get('username')
        self.password = account_config.get('password')
        self.use_ssl = account_config.get('use_ssl', True)
        
        self.imap_conn = None
    
    def connect_imap(self):
        """
        连接到 IMAP 服务器
        
        Returns:
            imaplib.IMAP4: IMAP 连接对象
        """
        try:
            if self.use_ssl:
                self.imap_conn = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            else:
                self.imap_conn = imaplib.IMAP4(self.imap_server, self.imap_port)
            
            self.imap_conn.login(self.username, self.password)
            logger.info(f"IMAP 登录成功：{self.username}")
            
            return self.imap_conn
            
        except Exception as e:
            logger.error(f"IMAP 连接失败：{e}")
            raise
    
    def disconnect_imap(self):
        """断开 IMAP 连接"""
        if self.imap_conn:
            try:
                self.imap_conn.close()
                self.imap_conn.logout()
                logger.debug("IMAP 连接已关闭")
            except Exception as e:
                logger.warning(f"关闭 IMAP 连接失败：{e}")
    
    def fetch_email_ids(self, folder='inbox', limit=None):
        """
        获取邮件 UID 列表（最新的在前）
        
        Args:
            folder: 文件夹名称，默认 'inbox'
            limit: 限制数量，None 表示全部
            
        Returns:
            list: 邮件 UID 列表（最新的在前）
        """
        try:
            if not self.imap_conn:
                self.connect_imap()
            
            # 选择文件夹
            self.imap_conn.select(folder)
            
            # 使用 UID 搜索所有邮件（UID 是持久的，不会因邮箱状态变化而改变）
            status, messages = self.imap_conn.uid('search', None, 'ALL')
            email_ids = messages[0].split()
            
            # 限制数量
            if limit and len(email_ids) > limit:
                email_ids = email_ids[-limit:]
            
            # 逆序排列（最新的在前）
            email_ids = list(reversed(email_ids))
            
            logger.info(f"获取到 {len(email_ids)} 封邮件")
            
            return [eid.decode() for eid in email_ids]
            
        except Exception as e:
            logger.error(f"获取邮件 ID 失败：{e}")
            raise
    
    def fetch_email_ids_with_offset(self, folder='inbox', limit=20, offset=0):
        """
        获取邮件 UID 列表，支持偏移量（用于分页加载）
        
        Args:
            folder: 文件夹名称，默认 'inbox'
            limit: 限制数量
            offset: 偏移量（跳过最新的 offset 封邮件）
            
        Returns:
            list: 邮件 UID 列表（最新的在前）
        """
        try:
            if not self.imap_conn:
                self.connect_imap()
            
            # 选择文件夹
            self.imap_conn.select(folder)
            
            # 使用 UID 搜索所有邮件
            status, messages = self.imap_conn.uid('search', None, 'ALL')
            all_email_ids = messages[0].split()
            
            # 逆序排列（最新的在前）
            all_email_ids = list(reversed(all_email_ids))
            
            # 应用偏移量和限制
            if offset >= len(all_email_ids):
                return []
            
            end_index = min(offset + limit, len(all_email_ids))
            email_ids = all_email_ids[offset:end_index]
            
            logger.info(f"获取到 {len(email_ids)} 封邮件（偏移量：{offset}）")
            
            return [eid.decode() for eid in email_ids]
            
        except Exception as e:
            logger.error(f"获取邮件 ID（带偏移）失败：{e}")
            raise
    
    def get_email_date(self, email_id, folder='inbox'):
        """
        获取邮件日期（仅获取 HEADER，不下载完整内容）
        
        Args:
            email_id: 邮件 UID
            folder: 文件夹名称
            
        Returns:
            str: 邮件日期字符串
        """
        try:
            if not self.imap_conn:
                self.connect_imap()
            
            self.imap_conn.select(folder)
            
            # 使用 UID 获取日期头信息
            status, msg_data = self.imap_conn.uid('fetch', email_id.encode(), '(BODY.PEEK[HEADER.FIELDS (DATE)])')
            
            if status == 'OK' and msg_data and msg_data[0]:
                header_data = msg_data[0][1]
                if header_data:
                    # 解析日期头
                    header_str = header_data.decode('utf-8', errors='replace')
                    for line in header_str.split('\n'):
                        if line.lower().startswith('date:'):
                            return line[5:].strip()
            
            return None
            
        except Exception as e:
            logger.warning(f"获取邮件 {email_id} 日期失败：{e}")
            return None
    
    def fetch_email_raw(self, email_id, folder='inbox'):
        """
        获取原始邮件数据
        
        Args:
            email_id: 邮件 UID
            folder: 文件夹名称，默认 'inbox'
            
        Returns:
            bytes: 原始 RFC822 格式的邮件数据
        """
        try:
            if not self.imap_conn:
                self.connect_imap()
            
            # 选择文件夹（FETCH 命令需要在 SELECTED 状态下执行）
            self.imap_conn.select(folder)
            
            # 使用 UID 获取邮件内容
            status, msg_data = self.imap_conn.uid('fetch', email_id.encode(), '(RFC822)')
            raw_email = msg_data[0][1]
            
            logger.debug(f"获取邮件 {email_id} 原始数据成功")
            
            return raw_email
            
        except Exception as e:
            logger.error(f"获取邮件数据失败：{e}")
            raise
    
    def fetch_emails_list(self, limit=20):
        """
        获取邮件列表（仅基本信息）
        
        Args:
            limit: 限制数量
            
        Returns:
            list: 邮件基本信息列表
        """
        from .email_parser import parse_email_from_bytes
        
        try:
            email_ids = self.fetch_email_ids(limit=limit)
            emails = []
            
            for email_id in email_ids:
                try:
                    raw_data = self.fetch_email_raw(email_id)
                    email_info = parse_email_from_bytes(raw_data)
                    email_info['id'] = email_id
                    
                    # 只保存基本信息，不缓存完整邮件
                    emails.append({
                        'id': email_info['id'],
                        'subject': email_info['subject'],
                        'from': email_info['from'],
                        'date': email_info['date'],
                        'preview': email_info['preview'],
                        'has_attachment': email_info['has_attachment'],
                    })
                    
                except Exception as e:
                    logger.warning(f"解析邮件 {email_id} 失败：{e}")
                    continue
            
            return emails
            
        except Exception as e:
            logger.error(f"获取邮件列表失败：{e}")
            raise
    
    def get_email_detail(self, email_id):
        """
        获取邮件详情
        
        Args:
            email_id: 邮件 ID
            
        Returns:
            dict: 邮件详情信息
        """
        from .email_parser import parse_email_from_bytes
        
        try:
            raw_data = self.fetch_email_raw(email_id)
            email_info = parse_email_from_bytes(raw_data)
            email_info['id'] = email_id
            
            return email_info
            
        except Exception as e:
            logger.error(f"获取邮件详情失败：{e}")
            raise
    
    def download_attachment(self, email_id, filename, save_path):
        """
        下载附件
        
        Args:
            email_id: 邮件 ID
            filename: 附件文件名
            save_path: 保存路径
            
        Returns:
            bool: 是否成功
        """
        try:
            raw_data = self.fetch_email_raw(email_id)
            email_obj = email.message_from_bytes(raw_data)
            
            # 查找并下载附件
            if email_obj.is_multipart():
                for part in email_obj.walk():
                    if part.get_content_maintype() == 'multipart':
                        continue
                    if part.get("Content-Disposition"):
                        part_filename = part.get_filename()
                        if part_filename == filename:
                            payload = part.get_payload(decode=True)
                            if payload:
                                with open(save_path, 'wb') as f:
                                    f.write(payload)
                                logger.info(f"附件已保存到：{save_path}")
                                return True
            
            logger.warning(f"未找到附件：{filename}")
            return False
            
        except Exception as e:
            logger.error(f"下载附件失败：{e}")
            return False
    
    def send_email(self, to, subject, body, attachments=None):
        """
        发送邮件
        
        Args:
            to: 收件人地址（多个用逗号分隔）
            subject: 主题
            body: 正文（HTML 格式）
            attachments: 附件文件路径列表
            
        Returns:
            bool: 是否成功
        """
        from email.mime.application import MIMEApplication
        import mimetypes
        
        try:
            # 创建邮件 - 使用 mixed 类型以支持附件
            msg = MIMEMultipart('mixed')
            msg['Subject'] = subject
            msg['From'] = self.username
            msg['To'] = to
            
            # 添加正文部分 - 使用 alternative 包装 HTML
            msg_body = MIMEMultipart('alternative')
            msg_body.attach(MIMEText(body, 'html', 'utf-8'))
            msg.attach(msg_body)
            
            # 添加附件
            if attachments:
                for file_path in attachments:
                    try:
                        filename = os.path.basename(file_path)
                        
                        # 猜测 MIME 类型
                        content_type, encoding = mimetypes.guess_type(file_path)
                        if content_type is None:
                            content_type = 'application/octet-stream'
                        main_type, sub_type = content_type.split('/', 1)
                        
                        with open(file_path, 'rb') as f:
                            file_data = f.read()
                            
                            # 使用 MIMEApplication 并指定正确的类型
                            attachment = MIMEApplication(file_data, _subtype=sub_type)
                            
                            # 添加 Content-Disposition 头，支持中文文件名
                            # 使用 RFC 5987 编码确保中文文件名正确显示
                            from email.utils import encode_rfc2231
                            
                            try:
                                # 尝试使用纯 ASCII 文件名
                                filename.encode('ascii')
                                disposition = f'attachment; filename="{filename}"'
                            except UnicodeEncodeError:
                                # 包含非 ASCII 字符，使用 RFC 5987 编码
                                encoded_filename = encode_rfc2231(filename, 'utf-8')
                                # encode_rfc2231 返回格式如: utf-8''%E4%B8%AD%E6%96%87
                                # 我们需要提取编码后的部分
                                disposition = f"attachment; filename*=utf-8''{encoded_filename[7:]}"
                            
                            attachment.add_header('Content-Disposition', disposition)
                            msg.attach(attachment)
                            
                            logger.info(f"附件添加成功：{filename} ({content_type})")
                    except Exception as e:
                        logger.error(f"添加附件失败：{file_path} - {e}")
                        raise
            
            # 发送邮件
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"邮件发送成功：{to}")
            return True
            
        except Exception as e:
            logger.error(f"发送邮件失败：{e}")
            return False
