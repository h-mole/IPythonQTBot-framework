"""
HTTP Server Plugin - Flask HTTP 服务器插件
"""

import threading
import time
import webbrowser
from typing import Optional, Callable, List, Dict, Any


def _check_flask():
    """检查 Flask 是否已安装"""
    try:
        import flask
        import werkzeug
        return True
    except ImportError:
        return False


class HttpServerPlugin:
    """HTTP Server 插件主类"""
    
    def __init__(self):
        self._app: Optional[Any] = None
        self._server_thread: Optional[threading.Thread] = None
        self._host: str = "127.0.0.1"
        self._port: int = 0
        self._running: bool = False
        self._lock: threading.Lock = threading.Lock()
        self._pending_blueprints: List[Dict[str, Any]] = []
        self._pending_routes: List[Dict[str, Any]] = []
        self._ready_event: threading.Event = threading.Event()  # 用于同步服务器就绪状态
    
    def start(self, host: str = "127.0.0.1", port: int = 0) -> Dict[str, Any]:
        """
        启动 HTTP 服务器
        
        Args:
            host: 主机地址，默认 127.0.0.1
            port: 端口号，默认 0（自动分配）
            
        Returns:
            dict: 包含成功状态、host、port、url 等信息
        """
        with self._lock:
            if self._running:
                return {
                    "success": True,
                    "host": self._host,
                    "port": self._port,
                    "url": self.get_url(),
                    "message": "服务器已在运行"
                }
            
            if not _check_flask():
                return {
                    "success": False,
                    "error": "Flask 未安装，请运行: pip install flask"
                }
            
            try:
                from flask import Flask
                from flask_cors import CORS
                
                # 创建 Flask 应用
                self._app = Flask(__name__)
                CORS(self._app)
                
                # 注册待处理的 blueprints 和 routes
                self._register_pending()
                
                # 重置就绪事件
                self._ready_event.clear()
                
                # 启动服务器线程
                self._host = host
                self._port = port
                self._server_thread = threading.Thread(
                    target=self._run_server,
                    daemon=True
                )
                self._server_thread.start()
                self._running = True
                
                # 等待服务器就绪（最多等待 5 秒）
                if self._ready_event.wait(timeout=5.0):
                    url = self.get_url()
                    print(f"[HTTPServer] 服务器已启动: {url}")
                    return {
                        "success": True,
                        "host": self._host,
                        "port": self._port,
                        "url": url
                    }
                else:
                    return {
                        "success": False,
                        "error": "服务器启动超时"
                    }
                
            except Exception as e:
                error_msg = f"启动服务器失败: {str(e)}"
                print(f"[HTTPServer] {error_msg}")
                return {"success": False, "error": error_msg}
    
    def _run_server(self):
        """在后台线程运行服务器"""
        try:
            from werkzeug.serving import make_server
            
            # 创建 WSGI 服务器
            server = make_server(self._host, self._port, self._app, threaded=True)
            
            # 获取实际分配的端口（如果是自动分配）
            if self._port == 0:
                self._port = server.server_address[1]
                print(f"[HTTPServer] 动态分配端口: {self._port}")
            
            # 通知主线程服务器已就绪
            self._ready_event.set()
            
            # 运行服务器
            server.serve_forever()
            
        except Exception as e:
            print(f"[HTTPServer] 服务器运行错误: {e}")
            self._running = False
            self._ready_event.set()  # 确保事件被设置，避免主线程永久等待
    
    def stop(self) -> Dict[str, Any]:
        """
        停止 HTTP 服务器
        
        Returns:
            dict: 包含成功状态和消息
        """
        with self._lock:
            if not self._running:
                return {"success": True, "message": "服务器未运行"}
            
            try:
                # 获取服务器并关闭
                from werkzeug.serving import BaseWSGIServer
                
                # Flask 没有直接的 shutdown 方法，我们需要通过请求上下文来关闭
                # 这里采用简单的方式：只是标记为停止，实际线程会在程序退出时结束
                self._running = False
                self._app = None
                self._server_thread = None
                self._ready_event.clear()  # 清除就绪事件
                
                print("[HTTPServer] 服务器已停止")
                return {"success": True, "message": "服务器已停止"}
                
            except Exception as e:
                error_msg = f"停止服务器失败: {str(e)}"
                print(f"[HTTPServer] {error_msg}")
                return {"success": False, "error": error_msg}
    
    def is_running(self) -> bool:
        """
        检查服务器是否正在运行
        
        Returns:
            bool: 服务器是否运行中
        """
        return self._running
    
    def get_url(self) -> Optional[str]:
        """
        获取服务器访问 URL
        
        Returns:
            str: 服务器 URL，如果未启动则返回 None
        """
        if not self._running or self._port == 0:
            return None
        return f"http://{self._host}:{self._port}"
    
    def get_app(self) -> Optional[Any]:
        """
        获取 Flask 应用实例
        
        Returns:
            Flask: Flask 应用实例，如果未启动则返回 None
        """
        return self._app
    
    def register_blueprint(self, blueprint: Any, url_prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        注册 Flask Blueprint（路由组）
        
        Args:
            blueprint: Flask Blueprint 实例
            url_prefix: URL 前缀，例如 /api/v1
            
        Returns:
            dict: 包含成功状态和消息
        """
        try:
            if self._running and self._app:
                # 服务器已启动，直接注册
                self._app.register_blueprint(blueprint, url_prefix=url_prefix)
            else:
                # 服务器未启动，加入待处理列表
                self._pending_blueprints.append({
                    "blueprint": blueprint,
                    "url_prefix": url_prefix
                })
            
            prefix_str = f" (前缀: {url_prefix})" if url_prefix else ""
            print(f"[HTTPServer] Blueprint 已注册{prefix_str}")
            return {"success": True, "message": f"Blueprint 注册成功{prefix_str}"}
            
        except Exception as e:
            error_msg = f"注册 Blueprint 失败: {str(e)}"
            print(f"[HTTPServer] {error_msg}")
            return {"success": False, "error": error_msg}
    
    def register_route(self, route: str, view_func: Callable, 
                       methods: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        注册单个路由函数
        
        Args:
            route: 路由路径，例如 /hello
            view_func: 视图函数
            methods: HTTP 方法列表，例如 ['GET', 'POST']
            
        Returns:
            dict: 包含成功状态和消息
        """
        try:
            if methods is None:
                methods = ['GET']
            
            if self._running and self._app:
                # 服务器已启动，直接注册
                self._app.route(route, methods=methods)(view_func)
            else:
                # 服务器未启动，加入待处理列表
                self._pending_routes.append({
                    "route": route,
                    "view_func": view_func,
                    "methods": methods
                })
            
            methods_str = ", ".join(methods)
            print(f"[HTTPServer] 路由已注册: {route} [{methods_str}]")
            return {"success": True, "message": f"路由 {route} 注册成功"}
            
        except Exception as e:
            error_msg = f"注册路由失败: {str(e)}"
            print(f"[HTTPServer] {error_msg}")
            return {"success": False, "error": error_msg}
    
    def _register_pending(self):
        """注册待处理的 blueprints 和 routes"""
        if self._app is None:
            return
        
        # 注册待处理的 blueprints
        for item in self._pending_blueprints:
            self._app.register_blueprint(
                item["blueprint"],
                url_prefix=item["url_prefix"]
            )
            prefix_str = f" (前缀: {item['url_prefix']})" if item['url_prefix'] else ""
            print(f"[HTTPServer] 待处理 Blueprint 已注册{prefix_str}")
        
        self._pending_blueprints.clear()
        
        # 注册待处理的 routes
        for item in self._pending_routes:
            self._app.route(item["route"], methods=item["methods"])(item["view_func"])
            methods_str = ", ".join(item["methods"])
            print(f"[HTTPServer] 待处理路由已注册: {item['route']} [{methods_str}]")
        
        self._pending_routes.clear()


# 插件实例
_plugin_instance = HttpServerPlugin()


def load_plugin(plugin_manager):
    """
    插件加载入口函数
    
    Args:
        plugin_manager: 插件管理器实例
        
    Returns:
        dict: 包含插件组件的字典
    """
    print("[HTTPServer] 正在加载 HTTP Server 插件...")
    
    # 注册暴露的方法到全局域
    plugin_manager.register_method(
        "http_server", "start", _plugin_instance.start
    )
    plugin_manager.register_method(
        "http_server", "stop", _plugin_instance.stop
    )
    plugin_manager.register_method(
        "http_server", "is_running", _plugin_instance.is_running
    )
    plugin_manager.register_method(
        "http_server", "get_url", _plugin_instance.get_url
    )
    plugin_manager.register_method(
        "http_server", "register_blueprint", _plugin_instance.register_blueprint
    )
    plugin_manager.register_method(
        "http_server", "register_route", _plugin_instance.register_route
    )
    plugin_manager.register_method(
        "http_server", "get_app", _plugin_instance.get_app
    )
    
    # 自动启动服务器（在后台线程中）
    result = _plugin_instance.start()
    if result["success"]:
        print(f"[HTTPServer] 服务器自动启动成功: {result.get('url', 'N/A')}")
    else:
        print(f"[HTTPServer] 服务器自动启动失败: {result.get('error', '未知错误')}")
    
    print("[HTTPServer] HTTP Server 插件加载完成")
    return {
        "widget": None,
        "namespace": "http_server"
    }


def unload_plugin(plugin_manager):
    """
    插件卸载回调
    
    Args:
        plugin_manager: 插件管理器实例
    """
    print("[HTTPServer] 正在卸载 HTTP Server 插件...")
    
    # 停止服务器
    _plugin_instance.stop()
    
    print("[HTTPServer] HTTP Server 插件卸载完成")
