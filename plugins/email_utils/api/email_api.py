"""
邮箱工具插件 - API 接口层
对外暴露统一的 API 接口供其他插件调用
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _parse_date_for_sort(date_str):
    """解析日期用于排序"""
    import email.utils
    try:
        parsed = email.utils.parsedate_to_datetime(date_str)
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
        return parsed
    except:
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%d %b %Y %H:%M:%S', '%d %b %Y %H:%M']:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
    return datetime.min


def get_incremental_emails_api(account_name: str, batch_size: int = 10):
    """
    API: 智能增量获取邮件
    拉取最新 batch_size 封邮件，如果全部未缓存，则继续拉取下一批
    直到发现已缓存的邮件或服务器没有更多邮件
    """
    from ..core.email_client import EmailClient
    from ..core.email_cache import EmailCacheManager
    from ..utils.helpers import get_account_config
    
    account_config = get_account_config(account_name)
    client = EmailClient(account_config)
    username = account_config.get('username')
    
    client.connect_imap()
    cache_manager = EmailCacheManager(username)
    cached_ids = cache_manager.get_cached_email_ids()
    
    all_new_emails = []
    offset = 0
    max_total = 1000
    
    while offset < max_total:
        if offset == 0:
            batch_ids = client.fetch_email_ids(limit=batch_size)
        else:
            batch_ids = client.fetch_email_ids_with_offset(limit=batch_size, offset=offset)
        
        if not batch_ids:
            break
        
        new_ids_in_batch = [eid for eid in batch_ids if eid not in cached_ids]
        
        for email_id in batch_ids:
            if email_id in cached_ids:
                try:
                    _, email_info = cache_manager.load_cached_email(email_id)
                    all_new_emails.append({
                        'id': email_info['id'],
                        'account': email_info.get('account', account_name),
                        'subject': email_info['subject'],
                        'from': email_info['from'],
                        'date': email_info['date'],
                        'preview': email_info['preview'],
                        'has_attachment': email_info['has_attachment'],
                    })
                except Exception as e:
                    try:
                        raw_data = client.fetch_email_raw(email_id)
                        email_info = cache_manager.save_email(email_id, raw_data, account=account_name)
                        all_new_emails.append(email_info)
                    except:
                        pass
            else:
                try:
                    raw_data = client.fetch_email_raw(email_id)
                    email_info = cache_manager.save_email(email_id, raw_data, account=account_name)
                    all_new_emails.append(email_info)
                except:
                    continue
        
        if len(new_ids_in_batch) < len(batch_ids):
            break
        
        offset += batch_size
        if offset >= max_total:
            break
    
    client.disconnect_imap()
    
    # 按日期倒序排序
    all_new_emails.sort(key=lambda x: _parse_date_for_sort(x.get('date', '')), reverse=True)
    
    return all_new_emails


def get_recent_emails_api(account_name: str, limit: int = 20, days: int = None):
    """
    API: 获取最近的邮件列表
    
    Args:
        account_name: 账号名称
        limit: 获取邮件数量限制，默认为 20
        days: 获取多少天内的邮件，默认为 None（不限制天数）
        
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
                    'account': email_info.get('account', account_name),
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


def get_recent_emails_with_history_api(account_name: str, limit: int = 20, days: int = None, 
                                       progress_callback=None):
    """
    API: 获取最近的邮件列表，支持拉取历史邮件和实时进度回调
    
    Args:
        account_name: 账号名称
        limit: 每批次获取邮件数量限制，默认为 20
        days: 获取多少天内的邮件，默认为 None（不限制天数）。
              如果指定，会持续拉取邮件直到达到日期限制或服务器没有更多邮件
        progress_callback: 进度回调函数，每获取一封新邮件调用一次，参数为 (email_info, current_count, total_new)
        
    Returns:
        list: 完整邮件列表（包含缓存和新获取的）
    """
    from ..core.email_client import EmailClient
    from ..core.email_cache import EmailCacheManager
    from ..utils.helpers import get_account_config
    
    account_config = get_account_config(account_name)
    client = EmailClient(account_config)
    username = account_config.get('username')
    
    # 连接服务器
    client.connect_imap()
    
    # 初始化缓存管理器
    cache_manager = EmailCacheManager(username)
    cached_ids = cache_manager.get_cached_email_ids()
    
    emails = []
    new_emails_count = 0
    
    # 计算截止日期
    cutoff_date = None
    if days is not None and days > 0:
        cutoff_date = datetime.now() - timedelta(days=days)
        logger.info(f"将拉取 {days} 天内的邮件（截止：{cutoff_date}）")
    
    # 获取服务器上的邮件 ID 列表（初始批次）
    batch_size = limit
    current_offset = 0
    all_server_ids = []
    
    # 第一批：获取最新的 limit 封邮件
    server_email_ids = client.fetch_email_ids(limit=batch_size)
    all_server_ids.extend(server_email_ids)
    
    # 如果需要获取历史邮件（days 参数），持续获取更多批次
    if days is not None and days > 0:
        while len(server_email_ids) == batch_size:
            # 检查当前批次中最老的邮件日期
            oldest_in_batch = None
            should_stop = False
            
            for email_id in reversed(server_email_ids):
                try:
                    # 快速获取邮件日期（使用 HEADER 获取，不下载完整内容）
                    date_str = client.get_email_date(email_id)
                    if date_str:
                        try:
                            email_date = parse_email_date(date_str)
                            if oldest_in_batch is None or email_date < oldest_in_batch:
                                oldest_in_batch = email_date
                            
                            # 如果这封邮件已经早于截止日期，可以停止
                            if email_date < cutoff_date:
                                should_stop = True
                                break
                        except:
                            pass
                except Exception as e:
                    logger.debug(f"获取邮件 {email_id} 日期失败：{e}")
            
            if should_stop:
                logger.info(f"已到达截止日期，停止获取更多邮件")
                break
            
            # 获取更多邮件
            current_offset += batch_size
            logger.info(f"获取更多邮件，偏移量：{current_offset}")
            
            try:
                more_ids = client.fetch_email_ids_with_offset(limit=batch_size, offset=current_offset)
                if not more_ids or len(more_ids) == 0:
                    break
                server_email_ids = more_ids
                all_server_ids.extend(server_email_ids)
            except Exception as e:
                logger.warning(f"获取更多邮件失败：{e}")
                break
    
    logger.info(f"共获取到 {len(all_server_ids)} 封邮件 ID 待处理")
    
    # 增量更新：只下载新邮件
    new_ids = [eid for eid in all_server_ids if eid not in cached_ids]
    logger.info(f"其中 {len(new_ids)} 封是新邮件")
    
    # 先加载缓存的邮件
    for email_id in all_server_ids:
        if email_id in cached_ids:
            # 从缓存加载
            try:
                _, email_info = cache_manager.load_cached_email(email_id)
                emails.append({
                    'id': email_info['id'],
                    'account': email_info.get('account', account_name),
                    'subject': email_info['subject'],
                    'from': email_info['from'],
                    'date': email_info['date'],
                    'preview': email_info['preview'],
                    'has_attachment': email_info['has_attachment'],
                })
            except Exception as e:
                logger.warning(f"加载缓存邮件失败 {email_id}: {e}")
                # 缓存损坏，重新从服务器获取
                try:
                    raw_data = client.fetch_email_raw(email_id)
                    email_info = cache_manager.save_email(email_id, raw_data, account=account_name)
                    emails.append(email_info)
                except Exception as e2:
                    logger.warning(f"重新获取邮件失败 {email_id}: {e2}")
                    continue
        else:
            # 新邮件，从服务器获取并缓存
            try:
                raw_data = client.fetch_email_raw(email_id)
                email_info = cache_manager.save_email(email_id, raw_data, account=account_name)
                emails.append(email_info)
                new_emails_count += 1
                
                # 调用进度回调
                if progress_callback:
                    try:
                        progress_callback(email_info, new_emails_count, len(new_ids))
                    except Exception as e:
                        logger.debug(f"进度回调执行失败：{e}")
                        
            except Exception as e:
                logger.warning(f"获取新邮件失败 {email_id}: {e}")
                continue
    
    # 断开连接
    client.disconnect_imap()
    
    # 按日期倒序排序
    emails.sort(key=lambda x: _parse_date_for_sort(x.get('date', '')), reverse=True)
    
    logger.info(f"共获取 {len(emails)} 封邮件，其中 {new_emails_count} 封是新邮件")
    return emails


def parse_email_date(date_str):
    """
    解析邮件日期字符串
    
    Args:
        date_str: 日期字符串
        
    Returns:
        datetime: 解析后的日期时间对象
    """
    import email.utils
    try:
        parsed = email.utils.parsedate_to_datetime(date_str)
        # 转换为本地时间（去掉时区信息）
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
        return parsed
    except:
        # 尝试其他格式
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%d %b %Y %H:%M:%S',
            '%d %b %Y %H:%M',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
        raise ValueError(f"无法解析日期：{date_str}")


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
        cache_manager.save_email(email_id, raw_data, account=account_name)
        
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


def reply_email_api(account_name: str, original_email_id: str, body: str, attachments: list = None):
    """
    API: 回复邮件
    
    Args:
        account_name: 账号名称
        original_email_id: 原邮件ID
        body: 回复的正文内容（HTML 格式）
        attachments: 附件文件路径列表
        
    Returns:
        bool: 发送是否成功
    """
    from ..core.email_client import EmailClient
    from ..core.email_cache import EmailCacheManager
    from ..utils.helpers import get_account_config
    
    account_config = get_account_config(account_name)
    username = account_config.get('username')
    client = EmailClient(account_config)
    
    # 获取原邮件详情
    cache_manager = EmailCacheManager(username)
    original_email = None
    
    # 优先从缓存加载
    if cache_manager.is_email_cached(original_email_id):
        try:
            _, original_email = cache_manager.load_cached_email(original_email_id)
        except Exception as e:
            logger.warning(f"加载缓存邮件失败 {original_email_id}: {e}")
    
    # 缓存中没有，从服务器获取
    if not original_email:
        try:
            client.connect_imap()
            original_email = client.get_email_detail(original_email_id)
            # 保存到缓存
            raw_data = client.fetch_email_raw(original_email_id)
            cache_manager.save_email(original_email_id, raw_data)
            client.disconnect_imap()
        except Exception as e:
            logger.error(f"获取原邮件详情失败：{e}")
            return False
    
    # 构建收件人（原邮件的发件人）
    to = original_email.get('from', '')
    if not to:
        logger.error("原邮件发件人为空，无法回复")
        return False
    
    # 构建主题（添加 Re: 前缀）
    original_subject = original_email.get('subject', '')
    if original_subject.startswith('Re:'):
        subject = original_subject
    else:
        subject = f"Re: {original_subject}"
    
    # 构建引用原文的邮件正文
    original_body = original_email.get('body', '')
    original_date = original_email.get('date', '')
    original_from = original_email.get('from', '')
    
    # 创建引用格式
    quoted_body = f"""
<div style="margin-top: 20px; border-top: 1px solid #ccc; padding-top: 10px; color: #666;">
    <div style="margin-bottom: 10px;">-------- 原始邮件 --------</div>
    <div><b>发件人:</b> {original_from}</div>
    <div><b>日期:</b> {original_date}</div>
    <div><b>主题:</b> {original_subject}</div>
    <br>
    <div style="white-space: pre-wrap;">{original_body}</div>
</div>
"""
    
    # 组合新正文和引用
    full_body = f"""
<div style="font-family: Arial, sans-serif;">
    {body}
    {quoted_body}
</div>
"""
    
    # 发送邮件
    return client.send_email(to, subject, full_body, attachments)


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


def get_cached_emails_by_days_api(account_name: str, days: int = 60):
    """
    API: 获取指定天数内的所有缓存邮件
    
    Args:
        account_name: 账号名称
        days: 获取多少天内的邮件，默认为 60 天
        
    Returns:
        list: 缓存邮件列表
    """
    from ..core.email_cache import EmailCacheManager
    from ..utils.helpers import get_account_config
    
    account_config = get_account_config(account_name)
    username = account_config.get('username')
    
    # 初始化缓存管理器
    cache_manager = EmailCacheManager(username)
    
    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # 获取所有缓存邮件
    all_cached = cache_manager.get_cached_emails_list()
    
    # 筛选在指定天数内的邮件
    filtered_emails = []
    for email in all_cached:
        try:
            date_str = email.get('date', '')
            if date_str:
                email_date = parse_email_date(date_str)
                if email_date >= cutoff_date:
                    filtered_emails.append(email)
        except Exception as e:
            logger.debug(f"解析日期失败 {email.get('id')}: {e}")
            # 如果日期解析失败，仍然包含该邮件
            filtered_emails.append(email)
    
    logger.info(f"从缓存加载了 {len(filtered_emails)} 封邮件（{days}天内）")
    return filtered_emails
