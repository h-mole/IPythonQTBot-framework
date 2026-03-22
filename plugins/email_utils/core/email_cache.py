"""
邮箱工具插件 - 邮件缓存管理
使用 EML 格式保存邮件，支持增量更新和离线查看
"""

import os
import email
from datetime import datetime
import logging
from .email_parser import parse_email_from_bytes
from ..utils.helpers import get_cache_dir

logger = logging.getLogger(__name__)


class EmailCacheManager:
    """邮件缓存管理器"""
    
    def __init__(self, username):
        """
        初始化缓存管理器
        
        Args:
            username: 邮箱用户名
        """
        self.username = username
        self.cache_dir = get_cache_dir(username)
        self.index_file = os.path.join(self.cache_dir, "index.json")
        self.email_index = {}  # email_id -> metadata
        
        # 加载索引
        self._load_index()
    
    def _load_index(self):
        """加载邮件索引"""
        try:
            if os.path.exists(self.index_file):
                import json
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    self.email_index = json.load(f)
                logger.info(f"加载了 {len(self.email_index)} 封缓存邮件")
        except Exception as e:
            logger.error(f"加载索引失败：{e}")
            self.email_index = {}
    
    def _save_index(self):
        """保存邮件索引"""
        try:
            import json
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.email_index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存索引失败：{e}")
    
    def save_email(self, email_id, raw_data):
        """
        保存邮件到缓存
        
        Args:
            email_id: 邮件 ID
            raw_data: 原始 RFC822 格式的邮件数据（字节）
            
        Returns:
            dict: 解析后的邮件元数据
        """
        try:
            # 保存为 EML 格式文件
            eml_path = os.path.join(self.cache_dir, f"{email_id}.eml")
            with open(eml_path, 'wb') as f:
                f.write(raw_data)
            
            # 解析邮件获取元数据
            email_info = parse_email_from_bytes(raw_data)
            
            # 更新索引
            self.email_index[email_id] = {
                'id': email_id,
                'subject': email_info['subject'],
                'from': email_info['from'],
                'date': email_info['date'],
                'preview': email_info['preview'],
                'has_attachment': email_info['has_attachment'],
                'cached_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            self._save_index()
            logger.debug(f"保存邮件缓存：{email_id}")
            
            return self.email_index[email_id]
            
        except Exception as e:
            logger.error(f"保存邮件缓存失败：{e}")
            raise
    
    def load_cached_email(self, email_id):
        """
        从缓存加载邮件
        
        Args:
            email_id: 邮件 ID
            
        Returns:
            tuple: (raw_data, email_info) 原始数据和解析后的信息
        """
        try:
            eml_path = os.path.join(self.cache_dir, f"{email_id}.eml")
            
            if not os.path.exists(eml_path):
                raise FileNotFoundError(f"缓存文件不存在：{email_id}")
            
            # 读取原始数据
            with open(eml_path, 'rb') as f:
                raw_data = f.read()
            
            # 解析邮件
            email_info = parse_email_from_bytes(raw_data)
            email_info['id'] = email_id
            
            return raw_data, email_info
            
        except Exception as e:
            logger.error(f"加载缓存邮件失败：{e}")
            raise
    
    def is_email_cached(self, email_id):
        """
        检查邮件是否已缓存
        
        Args:
            email_id: 邮件 ID
            
        Returns:
            bool: 是否已缓存
        """
        return email_id in self.email_index
    
    def get_cached_email_ids(self):
        """
        获取所有已缓存的邮件 ID
        
        Returns:
            set: 缓存的邮件 ID 集合
        """
        return set(self.email_index.keys())
    
    def get_cached_emails_list(self):
        """
        获取缓存邮件列表（仅元数据）
        
        Returns:
            list: 邮件元数据列表
        """
        # 按日期排序，最新的在前
        emails = sorted(
            self.email_index.values(),
            key=lambda x: x.get('date', ''),
            reverse=True
        )
        return emails
    
    def remove_email(self, email_id):
        """
        删除缓存的邮件
        
        Args:
            email_id: 邮件 ID
        """
        try:
            # 删除文件
            eml_path = os.path.join(self.cache_dir, f"{email_id}.eml")
            if os.path.exists(eml_path):
                os.remove(eml_path)
            
            # 从索引中移除
            if email_id in self.email_index:
                del self.email_index[email_id]
                self._save_index()
                
            logger.debug(f"删除缓存邮件：{email_id}")
            
        except Exception as e:
            logger.error(f"删除缓存邮件失败：{e}")
    
    def clear_cache(self):
        """清空所有缓存"""
        try:
            # 删除所有 EML 文件
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.eml'):
                    os.remove(os.path.join(self.cache_dir, filename))
            
            # 清空索引
            self.email_index = {}
            self._save_index()
            
            logger.info(f"清空了 {self.username} 的邮件缓存")
            
        except Exception as e:
            logger.error(f"清空缓存失败：{e}")
