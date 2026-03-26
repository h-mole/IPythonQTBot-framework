"""
Messages View Plugin - OpenAI Messages 可视化插件
"""

import os
import webbrowser
from typing import List, Dict, Any, Optional, Callable

from app_qt.plugin_manager import PluginManager


class MessagesViewPlugin:
    """Messages View 插件主类"""

    def __init__(self):
        self._current_messages: List[Dict[str, Any]] = []
        self._current_title: str = "Messages View"
        self._blueprint_registered: bool = False
        self._plugin_manager: Optional[PluginManager] = None

    def set_plugin_manager(self, plugin_manager: PluginManager):
        """设置插件管理器实例"""
        self._plugin_manager = plugin_manager

    def view_messages(
        self, messages: List[Dict[str, Any]], title: str = "Messages View"
    ) -> Dict[str, Any]:
        """
        在浏览器中展示 messages 列表

        Args:
            messages: OpenAI API 格式的 messages 列表（list of dict）
            title: 页面标题

        Returns:
            dict: 包含成功状态和 URL
        """
        # 验证 messages 参数
        if not isinstance(messages, list):
            return {"success": False, "error": "messages 必须是列表类型"}

        if self._plugin_manager is None:
            return {"success": False, "error": "插件管理器未设置"}
        
        # 更新消息数据
        self._current_messages = messages
        self._current_title = title

        # 获取服务器 URL 并打开浏览器
        http_get_url = self._plugin_manager.get_method("http_server.get_url")
        url = http_get_url()

        if url:
            view_url = f"{url}/messages-view/"
            webbrowser.open(view_url)
            return {"success": True, "url": view_url, "message_count": len(messages)}
        else:
            return {"success": False, "error": "无法获取服务器 URL"}

    def _register_blueprint(self) -> Dict[str, Any]:
        """
        注册 Flask Blueprint

        Returns:
            dict: 包含成功状态和消息
        """
        try:
            from flask import Blueprint, jsonify, send_from_directory

            # 创建 Blueprint
            bp = Blueprint("messages_view", __name__)

            # 获取模板目录
            template_dir = os.path.dirname(os.path.abspath(__file__))

            @bp.route("/")
            def index():
                """主页 - 返回 HTML 模板"""
                return send_from_directory(template_dir, "template.html")

            @bp.route("/api/messages")
            def get_messages():
                """API - 返回消息数据"""
                return jsonify(
                    {"messages": self._current_messages, "title": self._current_title}
                )

            self._plugin_manager.agent_request_view_messages_signal.connect(
                self.view_messages
            )
            # 注册 Blueprint
            register_blueprint = self._plugin_manager.get_method(
                "http_server.register_blueprint"
            )
            result = register_blueprint(blueprint=bp, url_prefix="/messages-view")

            if result["success"]:
                self._blueprint_registered = True
                print("[MessagesView] Blueprint 注册成功，前缀: /messages-view")

            return result

        except Exception as e:
            error_msg = f"注册 Blueprint 失败: {str(e)}"
            print(f"[MessagesView] {error_msg}")
            return {"success": False, "error": error_msg}

    def on_unload(self):
        if self._plugin_manager is not None:
            # 释放插件管理器引用
            self._plugin_manager.agent_request_view_messages_signal.disconnect(
                self.view_messages
            )


# 插件实例
_plugin_instance = None


def load_plugin(plugin_manager: PluginManager):
    """
    插件加载入口函数

    Args:
        plugin_manager: 插件管理器实例

    Returns:
        dict: 包含插件组件的字典
    """
    global _plugin_instance
    print("[MessagesView] 正在加载 Messages View 插件...")
    _plugin_instance = MessagesViewPlugin()
    # 检查 http_server 插件是否可用
    if not plugin_manager.is_plugin_loaded("http_server"):
        error_msg = "http_server 插件未加载，请先加载 http_server 插件"
        print(f"[MessagesView] 错误: {error_msg}")
        return {"widget": None, "namespace": "messages_view", "error": error_msg}

    # 设置 plugin_manager
    _plugin_instance.set_plugin_manager(plugin_manager)

    # 注册暴露的方法到全局域
    plugin_manager.register_method(
        "messages_view", "view_messages", _plugin_instance.view_messages
    )

    # 立即注册 Blueprint（服务器已启动）
    result = _plugin_instance._register_blueprint()
    if result["success"]:
        print("[MessagesView] Blueprint 注册成功")
    else:
        print(f"[MessagesView] Blueprint 注册失败: {result.get('error')}")

    print("[MessagesView] Messages View 插件加载完成")
    return {"widget": None, "namespace": "messages_view"}


def unload_plugin(plugin_manager: PluginManager):
    """
    插件卸载回调

    Args:
        plugin_manager: 插件管理器实例
    """
    print("[MessagesView] 正在卸载 Messages View 插件...")
    print("[MessagesView] Messages View 插件卸载完成")
    if _plugin_instance is not None:
        _plugin_instance.on_unload()
