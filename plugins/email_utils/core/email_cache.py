"""
邮箱工具插件 - 邮件缓存管理
使用 EML 格式保存邮件，支持增量更新和离线查看
"""

import os
import email
import csv
from datetime import datetime
import logging
from html.parser import HTMLParser
from .email_parser import parse_email_from_bytes
from ..utils.helpers import get_cache_dir

logger = logging.getLogger(__name__)


class MLStripper(HTMLParser):
    """HTML 标签剥离器，用于提取纯文本"""
    
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []
        self.convert_charrefs = True

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_html_tags(html_text):
    """去除 HTML 标签，提取纯文本"""
    if not html_text:
        return ""
    try:
        s = MLStripper()
        s.feed(html_text)
        text = s.get_data()
        lines = [line.strip() for line in text.splitlines()]
        text = ' '.join(line for line in lines if line)
        return text
    except Exception as e:
        logger.warning(f"HTML 解析失败：{e}")
        return html_text


def extract_plain_preview(email_info):
    """从邮件信息中提取纯文本预览"""
    preview = email_info.get('preview', '')
    if preview and ('<' in preview and '>' in preview):
        preview = strip_html_tags(preview)
    preview = preview.strip()
    if len(preview) > 200:
        preview = preview[:200] + '...'
    return preview


class EmailCacheManager:
    """邮件缓存管理器"""
    
    CSV_HEADERS = ['id', 'account', 'subject', 'from', 'date', 'preview', 'has_attachment', 'cached_time']
    
    def __init__(self, username):
        self.username = username
        self.cache_dir = get_cache_dir(username)
        self.index_file = os.path.join(self.cache_dir, "index.csv")
        self.email_index = {}
        self._load_index()
    
    def _load_index(self):
        """加载邮件索引（从 CSV），兼容旧数据格式"""
        try:
            if os.path.exists(self.index_file):
                with open(self.index_file, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        email_id = row['id']
                        row['has_attachment'] = row['has_attachment'].lower() == 'true'
                        if 'account' not in row or not row['account']:
                            row['account'] = self.username
                        self.email_index[email_id] = row
                logger.info(f"加载了 {len(self.email_index)} 封缓存邮件")
        except Exception as e:
            logger.error(f"加载索引失败：{e}")
            self.email_index = {}
    
    def _save_index(self):
        """保存邮件索引（覆盖写入整个 CSV）"""
        try:
            with open(self.index_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_HEADERS)
                writer.writeheader()
                for email_id, metadata in self.email_index.items():
                    writer.writerow(metadata)
        except Exception as e:
            logger.error(f"保存索引失败：{e}")
    
    def _append_to_index(self, metadata):
        """追加单条记录到索引 CSV"""
        try:
            file_exists = os.path.exists(self.index_file) and os.path.getsize(self.index_file) > 0
            with open(self.index_file, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_HEADERS)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(metadata)
        except Exception as e:
            logger.error(f"追加索引失败：{e}")
    
    def save_email(self, email_id, raw_data, account=None):
        """保存邮件到缓存"""
        try:
            eml_path = os.path.join(self.cache_dir, f"{email_id}.eml")
            with open(eml_path, 'wb') as f:
                f.write(raw_data)
            
            email_info = parse_email_from_bytes(raw_data)
            preview = extract_plain_preview(email_info)
            account_name = account if account else self.username
            
            metadata = {
                'id': email_id,
                'account': account_name,
                'subject': email_info['subject'],
                'from': email_info['from'],
                'date': email_info['date'],
                'preview': preview,
                'has_attachment': email_info['has_attachment'],
                'cached_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            self.email_index[email_id] = metadata
            self._append_to_index(metadata)
            logger.debug(f"保存邮件缓存：{email_id}")
            return metadata
            
        except Exception as e:
            logger.error(f"保存邮件缓存失败：{e}")
            raise
    
    def load_cached_email(self, email_id):
        """从缓存加载邮件"""
        try:
            eml_path = os.path.join(self.cache_dir, f"{email_id}.eml")
            if not os.path.exists(eml_path):
                raise FileNotFoundError(f"缓存文件不存在：{email_id}")
            
            with open(eml_path, 'rb') as f:
                raw_data = f.read()
            
            email_info = parse_email_from_bytes(raw_data)
            email_info['id'] = email_id
            
            if email_id in self.email_index:
                email_info['account'] = self.email_index[email_id].get('account', self.username)
            else:
                email_info['account'] = self.username
            
            return raw_data, email_info
            
        except Exception as e:
            logger.error(f"加载缓存邮件失败：{e}")
            raise
    
    def is_email_cached(self, email_id):
        """检查邮件是否已缓存"""
        return email_id in self.email_index
    
    def get_cached_email_ids(self):
        """获取所有已缓存的邮件 ID"""
        return set(self.email_index.keys())
    
    def get_cached_emails_list(self):
        """获取缓存邮件列表（仅元数据）"""
        emails = sorted(
            self.email_index.values(),
            key=lambda x: x.get('date', ''),
            reverse=True
        )
        return emails
    
    def remove_email(self, email_id):
        """删除缓存的邮件"""
        try:
            eml_path = os.path.join(self.cache_dir, f"{email_id}.eml")
            if os.path.exists(eml_path):
                os.remove(eml_path)
            
            if email_id in self.email_index:
                del self.email_index[email_id]
                self._save_index()
                
            logger.debug(f"删除缓存邮件：{email_id}")
            
        except Exception as e:
            logger.error(f"删除缓存邮件失败：{e}")
    
    def clear_cache(self):
        """清空所有缓存"""
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.eml'):
                    os.remove(os.path.join(self.cache_dir, filename))
            
            self.email_index = {}
            if os.path.exists(self.index_file):
                os.remove(self.index_file)
            
            logger.info(f"清空了 {self.username} 的邮件缓存")
            
        except Exception as e:
            logger.error(f"清空缓存失败：{e}")
