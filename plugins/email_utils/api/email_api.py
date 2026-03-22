"""
邮箱工具插件 - API 接口层
对外暴露统一的 API 接口供其他插件调用
"""

import logging

logger = logging.getLogger(__name__)


def get_recent_emails_api(account_name: str, limit: int = 20):
    """
    API: 获取最近的邮件列表
    
    Args:
        account_name: 账号名称
        limit: 获取邮件数量限制，默认为 20
        
    Returns:
        list: 邮件列表
    """
    from ..core.email_client import EmailClient
    from ..core.email_cache import EmailCacheManager
    from ..utils.helpers import get_account_config
    
    account_config = get_account_config(account_name)
    client = EmailClient(account_config)
    username = account_config.get('username')
    
    # 连接服务器
    client.connect_imap()
    
    # 获取服务器上的邮件 ID 列表
    server_email_ids = client.fetch_email_ids(limit=limit)
    
    # 初始化缓存管理器
    cache_manager = EmailCacheManager(username)
    cached_ids = cache_manager.get_cached_email_ids()
    
    emails = []
    
    # 增量更新：只下载新邮件
    new_ids = set(server_email_ids) - cached_ids
    logger.info(f"发现 {len(new_ids)} 封新邮件")
    
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
    
    return emails


def get_email_detail_api(account_name, email_id):
    """
    API: 获取邮件详情
    
    Args:
        account_name: 账号名称
        email_id: 邮件 ID
        
    Returns:
        dict: 邮件详情
    """
    from ..core.email_client import EmailClient
    from ..core.email_cache import EmailCacheManager
    from ..utils.helpers import get_account_config
    
    account_config = get_account_config(account_name)
    username = account_config.get('username')
    
    # 初始化缓存管理器
    cache_manager = EmailCacheManager(username)
    
    # 优先从缓存加载
    if cache_manager.is_email_cached(email_id):
        try:
            _, email_info = cache_manager.load_cached_email(email_id)
            logger.info(f"从缓存加载邮件详情：{email_id}")
            return email_info
        except Exception as e:
            logger.warning(f"缓存加载失败 {email_id}: {e}")
    
    # 从服务器获取
    try:
        client = EmailClient(account_config)
        client.connect_imap()
        email_info = client.get_email_detail(email_id)
        client.disconnect_imap()
        
        # 保存到缓存
        raw_data = client.fetch_email_raw(email_id)
        cache_manager.save_email(email_id, raw_data)
        
        return email_info
        
    except Exception as e:
        logger.error(f"获取邮件详情失败：{e}")
        raise


def send_email_api(account_name: str, to: str, subject: str, body: str, attachments: list = None):
    """
    API: 发送邮件
    
    Args:
        account_name: 账号名称
        to: 收件人邮箱（多个用逗号分隔）
        subject: 邮件主题
        body: 邮件正文（HTML 格式）
        attachments: 附件文件路径列表
        
    Returns:
        bool: 发送是否成功
    """
    from ..core.email_client import EmailClient
    from ..utils.helpers import get_account_config
    
    account_config = get_account_config(account_name)
    client = EmailClient(account_config)
    
    return client.send_email(to, subject, body, attachments)


def get_attachments_api(account_name, email_id):
    """
    API: 获取邮件附件列表
    
    Args:
        account_name: 账号名称
        email_id: 邮件 ID
        
    Returns:
        list: 附件列表
    """
    detail = get_email_detail_api(account_name, email_id)
    return detail.get('attachments', [])


def download_attachment_api(account_name, email_id, filename, save_path):
    """
    API: 下载附件
    
    Args:
        account_name: 账号名称
        email_id: 邮件 ID
        filename: 附件文件名
        save_path: 保存路径
        
    Returns:
        bool: 是否成功
    """
    from ..core.email_client import EmailClient
    from ..utils.helpers import get_account_config
    
    account_config = get_account_config(account_name)
    client = EmailClient(account_config)
    
    return client.download_attachment(email_id, filename, save_path)


def get_accounts_api():
    """
    API: 获取所有配置的邮箱账号
    
    Returns:
        list: 账号列表（不包含密码）
    """
    from ..utils.helpers import load_accounts_config
    
    accounts = load_accounts_config()
    
    # 不返回密码
    safe_accounts = []
    for acc in accounts:
        safe_acc = acc.copy()
        safe_acc.pop('password', None)
        safe_accounts.append(safe_acc)
    
    return safe_accounts
