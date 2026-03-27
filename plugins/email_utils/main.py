"""
邮箱工具插件 - 主程序
提供邮件收发、管理和预览功能

重构后版本 - 组件化架构
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Initialize plugin i18n
from app_qt.plugin_i18n import PluginI18n
_i18n = PluginI18n("email_utils", Path(__file__).parent)
_ = _i18n.gettext


# ==================== 插件入口函数 ====================

def load_plugin(plugin_manager):
    """
    插件加载入口函数
    
    Args:
        plugin_manager: 插件管理器实例
    
    Returns:
        dict: 包含插件组件的字典
    """
    print(_("[EmailUtils] Loading email plugin..."))
    
    # 创建标签页实例
    from .components.email_list_widget import EmailListWidget
    email_tab = EmailListWidget(plugin_manager=plugin_manager)
    
    # 连接邮件详情请求信号
    email_tab.email_detail_requested.connect(
        lambda email_id, account_name: show_email_detail_dialog(email_tab, email_id, account_name)
    )
    
    # 注册暴露的方法到全局域
    from .api.email_api import (
        get_recent_emails_api,
        get_email_detail_api,
        send_email_api,
        get_attachments_api,
        download_attachment_api,
        get_accounts_api,reply_email_api
    )
    
    plugin_manager.register_method(
        "email_utils", "get_recent_emails", get_recent_emails_api,
        extra_data={"enable_mcp": True}
    )
    plugin_manager.register_method(
        "email_utils", "get_email_detail", get_email_detail_api
    )
    plugin_manager.register_method(
        "email_utils", "send_email", send_email_api,
        extra_data={"enable_mcp": True}
    )
    plugin_manager.register_method(
        "email_utils", "reply_email", reply_email_api,
        extra_data={"enable_mcp": True}
    )
    plugin_manager.register_method(
        "email_utils", "get_attachments", get_attachments_api
    )
    plugin_manager.register_method(
        "email_utils", "download_attachment", download_attachment_api
    )
    plugin_manager.register_method(
        "email_utils", "get_accounts", get_accounts_api,
        extra_data={"enable_mcp": True}
    )
    
    # 添加到标签页
    plugin_manager.add_plugin_tab("email_utils", _("📧 Email Manager"), email_tab, position=2)
    
    print(_("[EmailUtils] Email plugin loaded"))
    return {"tab": email_tab, "namespace": "email_utils"}


def show_email_detail_dialog(email_tab, email_id, account_name):
    """
    显示邮件详情对话框
    
    Args:
        email_tab: 邮件列表组件实例
        email_id: 邮件 ID
        account_name: 邮件所属的账号名称
    """
    try:
        from .components.email_detail_dialog import EmailDetailDialog
        from .api.email_api import get_email_detail_api
        
        if not account_name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(email_tab, _("Warning"), _("Cannot determine email account!"))
            return
        
        # 获取邮件详情
        email_detail = get_email_detail_api(account_name, email_id)
        
        # 创建并显示对话框
        dialog = EmailDetailDialog(
            email_tab.parent(), 
            email_detail=email_detail, 
            account_name=account_name
        )
        dialog.exec()
        
    except Exception as e:
        logger.error(f"显示邮件详情失败：{e}", exc_info=True)
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(email_tab, _("Error"), _("Failed to load email details: {}") + str(e))


def unload_plugin(plugin_manager):
    """
    插件卸载回调
    
    Args:
        plugin_manager: 插件管理器实例
    """
    print(_("[EmailUtils] Unloading email plugin..."))
    # 清理资源、保存状态等
    print(_("[EmailUtils] Email plugin unloaded"))
