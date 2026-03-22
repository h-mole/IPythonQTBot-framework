"""
邮箱工具插件 - 邮件解析器
负责解码邮件头、提取正文和附件信息
"""

import email
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


def decode_header(header):
    """
    解码邮件头
    
    Args:
        header: 邮件头字符串
        
    Returns:
        str: 解码后的字符串
    """
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


def extract_email_body(email_obj):
    """
    提取邮件正文
    
    Args:
        email_obj: email.message 对象
        
    Returns:
        tuple: (body_plain, body_html) 纯文本和 HTML 格式的正文
    """
    body_plain = ''
    body_html = ''
    
    if email_obj.is_multipart():
        for part in email_obj.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            # 优先获取 text/plain
            if content_type == 'text/plain' and 'attachment' not in content_disposition:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body_plain = payload.decode(charset, errors='replace')
                        break
                except Exception as e:
                    logger.debug(f"提取纯文本失败：{e}")
                    
            # 获取 text/html
            elif content_type == 'text/html' and not body_html:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body_html = payload.decode(charset, errors='replace')
                except Exception as e:
                    logger.debug(f"提取 HTML 失败：{e}")
    else:
        # 不是 multipart
        try:
            payload = email_obj.get_payload(decode=True)
            if payload:
                charset = email_obj.get_content_charset() or 'utf-8'
                body_plain = payload.decode(charset, errors='replace')
        except Exception as e:
            logger.debug(f"提取正文失败：{e}")
    
    return body_plain, body_html


def extract_attachments_info(email_obj):
    """
    提取附件信息
    
    Args:
        email_obj: email.message 对象
        
    Returns:
        list: 附件信息列表，每个元素包含 filename, size, content_type
    """
    attachments = []
    
    if email_obj.is_multipart():
        for part in email_obj.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get("Content-Disposition"):
                filename = part.get_filename()
                if filename:
                    payload = part.get_payload(decode=True) or b''
                    attachments.append({
                        'filename': filename,
                        'size': len(payload),
                        'content_type': part.get_content_type(),
                    })
    
    return attachments


def has_attachment(email_obj):
    """
    检查邮件是否有附件
    
    Args:
        email_obj: email.message 对象
        
    Returns:
        bool: 是否有附件
    """
    if email_obj.is_multipart():
        for part in email_obj.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get("Content-Disposition"):
                return True
    return False


def parse_email_from_bytes(raw_email):
    """
    从原始字节数据解析邮件
    
    Args:
        raw_email: 原始 RFC822 格式的邮件字节数据
        
    Returns:
        dict: 解析后的邮件信息
    """
    email_obj = email.message_from_bytes(raw_email)
    
    # 提取基本信息
    subject = decode_header(email_obj.get('Subject', ''))
    from_str = decode_header(email_obj.get('From', ''))
    to_str = decode_header(email_obj.get('To', ''))
    
    # 提取日期
    date_str = email_obj.get('Date', '')
    try:
        date_obj = email.utils.parsedate_to_datetime(date_str)
        date_display = date_obj.strftime('%Y-%m-%d %H:%M')
    except:
        date_display = date_str
    
    # 提取正文
    body_plain, body_html = extract_email_body(email_obj)
    
    # 提取附件信息
    attachments = extract_attachments_info(email_obj)
    
    # 生成预览
    preview_text = body_plain[:100] + '...' if len(body_plain) > 100 else body_plain
    if not preview_text.strip() and body_html:
        # 如果没有纯文本，从 HTML 提取
        soup = BeautifulSoup(body_html, 'html.parser')
        preview_text = soup.get_text()[:100] + '...' if len(soup.get_text()) > 100 else soup.get_text()
    
    return {
        'subject': subject,
        'from': from_str,
        'to': to_str,
        'date': date_display,
        'body_plain': body_plain,
        'body_html': body_html,
        'attachments': attachments,
        'has_attachment': len(attachments) > 0,
        'preview': preview_text.strip(),
    }
