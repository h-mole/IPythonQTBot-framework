"""
邮箱工具插件 - 辅助函数
提供配置文件读写、目录管理、日志记录等功能
"""

import os
import json
import logging
from app_qt.configs import PLUGIN_DATA_DIR

logger = logging.getLogger(__name__)

# 插件数据目录
EMAIL_UTILS_DATA_DIR = os.path.join(PLUGIN_DATA_DIR, "email_utils")
CONFIG_FILE = os.path.join(EMAIL_UTILS_DATA_DIR, "email_accounts.json")


def ensure_data_dir():
    """确保数据目录存在"""
    os.makedirs(EMAIL_UTILS_DATA_DIR, exist_ok=True)


def get_cache_dir(username):
    """
    获取指定用户名的缓存目录
    
    Args:
        username: 邮箱用户名
        
    Returns:
        str: 缓存目录路径
    """
    cache_dir = os.path.join(EMAIL_UTILS_DATA_DIR, username, "inbox")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def load_accounts_config():
    """
    加载账号配置
    
    Returns:
        list: 账号配置列表
    """
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("accounts", [])
        else:
            return []
    except Exception as e:
        logger.error(f"加载账号配置失败：{e}")
        return []


def save_accounts_config(accounts_config):
    """
    保存账号配置
    
    Args:
        accounts_config: 账号配置列表
    """
    try:
        ensure_data_dir()
        data = {"accounts": accounts_config}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"保存账号配置失败：{e}")


def get_account_config(account_name):
    """
    根据账号名称获取配置
    
    Args:
        account_name: 账号名称
        
    Returns:
        dict: 账号配置
        
    Raises:
        ValueError: 未找到配置
    """
    accounts = load_accounts_config()
    for acc in accounts:
        if acc.get("name") == account_name:
            return acc
    
    raise ValueError(f"未找到账号配置：{account_name}")
