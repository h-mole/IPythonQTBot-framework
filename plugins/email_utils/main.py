"""
邮箱工具插件 - 主程序
提供邮件收发、管理和预览功能

重构后版本 - 组件化架构
"""

import logging

logger = logging.getLogger(__name__)


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
    from .components.email_list_widget import EmailListWidget
    email_tab = EmailListWidget(plugin_manager=plugin_manager)
    
    # 注册暴露的方法到全局域
    from .api.email_api import (
        get_recent_emails_api,
        get_email_detail_api,
        send_email_api,
        get_attachments_api,
        download_attachment_api,
        get_accounts_api,
    )
    
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
