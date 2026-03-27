"""
Network Previewer Plugin - NetworkX 网络可视化插件
"""

import os
import json
import webbrowser
from typing import Dict, Any, Optional

from app_qt.plugin_manager import PluginManager


class NetworkPreviewerPlugin:
    """Network Previewer 插件主类"""

    def __init__(self):
        self._current_graph_data: Dict[str, Any] = {"nodes": [], "edges": []}
        self._current_title: str = "Network View"
        self._current_options: Dict[str, Any] = {}
        self._blueprint_registered: bool = False
        self._plugin_manager: Optional[PluginManager] = None

    def set_plugin_manager(self, plugin_manager: PluginManager):
        """设置插件管理器实例"""
        self._plugin_manager = plugin_manager

    def view_network(
        self, 
        graph, 
        title: str = "Network View",
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        在浏览器中可视化展示 NetworkX 图

        Args:
            graph: NetworkX 图对象
            title: 页面标题
            options: vis-network 配置选项（可选）

        Returns:
            dict: 包含成功状态和 URL
        """
        # 验证 graph 参数
        if graph is None:
            return {"success": False, "error": "graph 不能为空"}

        if self._plugin_manager is None:
            return {"success": False, "error": "插件管理器未设置"}
        
        try:
            # 转换 NetworkX 图为 vis-network 格式
            graph_data = self._convert_graph(graph)
            
            # 更新图数据
            self._current_graph_data = graph_data
            self._current_title = title
            self._current_options = options or {}

            # 获取服务器 URL 并打开浏览器
            http_get_url = self._plugin_manager.get_method("http_server.get_url")
            url = http_get_url()

            if url:
                view_url = f"{url}/network-preview/"
                webbrowser.open(view_url)
                return {
                    "success": True, 
                    "url": view_url, 
                    "node_count": len(graph_data["nodes"]),
                    "edge_count": len(graph_data["edges"])
                }
            else:
                return {"success": False, "error": "无法获取服务器 URL"}
                
        except Exception as e:
            return {"success": False, "error": f"转换图数据失败: {str(e)}"}

    def _convert_graph(self, graph) -> Dict[str, Any]:
        """
        将 NetworkX 图转换为 vis-network 格式

        Args:
            graph: NetworkX 图对象

        Returns:
            dict: 包含 nodes 和 edges 的字典
        """
        import networkx as nx
        
        nodes = []
        edges = []
        
        # 转换节点
        for node_id in graph.nodes():
            node_data = graph.nodes[node_id]
            node = {
                "id": str(node_id),
                "label": str(node_data.get("label", node_id)),
            }
            
            # DOT 读取时属性可能带引号，需要处理
            def get_attr(data, key):
                # 尝试多种可能的键名
                for k in [key, f'"{key}"', f"'{key}'"]:
                    if k in data:
                        val = data[k]
                        # 去除字符串值的引号
                        if isinstance(val, str):
                            val = val.strip('"').strip("'")
                        return val
                return None
            
            # 添加其他属性
            title = get_attr(node_data, "tooltip") or get_attr(node_data, "title")
            if title:
                node["title"] = str(title)
            
            group = get_attr(node_data, "group")
            if group:
                node["group"] = str(group)
            
            value = get_attr(node_data, "value")
            if value:
                try:
                    node["value"] = float(value)
                except:
                    node["value"] = value
            
            # 处理颜色：DOT 中的 fillcolor 和 color（边框）
            # vis-network 需要对象格式: {background: '...', border: '...'}
            fill_color = get_attr(node_data, "fillcolor")
            border_color = get_attr(node_data, "color")
            
            if fill_color or border_color:
                bg_color = fill_color or border_color
                border = border_color if border_color and border_color != bg_color else bg_color
                node["color"] = {
                    "background": bg_color,
                    "border": border,
                    "highlight": {
                        "background": bg_color,
                        "border": border_color if border_color and border_color != bg_color else "#000000"
                    }
                }
            elif "color" in node_data and isinstance(node_data["color"], dict):
                # 已经是 vis-network 格式
                node["color"] = node_data["color"]
            
            shape = get_attr(node_data, "shape")
            if shape:
                node["shape"] = shape
            
            image = get_attr(node_data, "image")
            if image:
                node["image"] = image
                node["shape"] = "image"
            
            # 添加其他自定义数据
            for key, value in node_data.items():
                clean_key = key.strip('"').strip("'")
                if clean_key not in node and clean_key not in ["label", "title", "group", "value", "color", "fillcolor", "shape", "image", "tooltip"]:
                    if isinstance(value, str):
                        value = value.strip('"').strip("'")
                    if clean_key not in node:
                        node[clean_key] = value
            nodes.append(node)
        
        # 转换边
        for source, target, edge_data in graph.edges(data=True):
            edge = {
                "from": str(source),
                "to": str(target),
            }
            
            # DOT 读取时属性可能带引号，需要处理
            def get_edge_attr(data, key):
                for k in [key, f'"{key}"', f"'{key}'"]:
                    if k in data:
                        val = data[k]
                        if isinstance(val, str):
                            val = val.strip('"').strip("'")
                        return val
                return None
            
            # 添加标签
            label = get_edge_attr(edge_data, "label")
            if label:
                edge["label"] = str(label)
            
            # 添加标题（悬停提示）
            title = get_edge_attr(edge_data, "title")
            if title:
                edge["title"] = str(title)
            
            # 添加边的值（影响线条粗细）
            value = get_edge_attr(edge_data, "value")
            if value:
                try:
                    edge["value"] = float(value)
                except:
                    edge["value"] = value
            # 添加边的颜色
            color_val = get_edge_attr(edge_data, "color")
            if color_val:
                edge["color"] = {"color": color_val}
            # 添加箭头配置
            arrows = get_edge_attr(edge_data, "arrows")
            if arrows:
                edge["arrows"] = arrows
            elif isinstance(graph, nx.DiGraph):
                edge["arrows"] = "to"
            # 添加虚线配置（DOT 中用 style=dashed）
            style = get_edge_attr(edge_data, "style")
            if style and "dashed" in style.lower():
                edge["dashes"] = True
            elif "dashes" in edge_data:
                edge["dashes"] = edge_data["dashes"]
            
            # 添加自定义数据
            for key, value in edge_data.items():
                clean_key = key.strip('"').strip("'")
                if clean_key not in edge and clean_key not in ["label", "title", "value", "color", "arrows", "dashes", "style"]:
                    if isinstance(value, str):
                        value = value.strip('"').strip("'")
                    edge[clean_key] = value
            edges.append(edge)
        
        return {"nodes": nodes, "edges": edges}

    def _register_blueprint(self) -> Dict[str, Any]:
        """
        注册 Flask Blueprint

        Returns:
            dict: 包含成功状态和消息
        """
        try:
            from flask import Blueprint, jsonify, send_from_directory

            # 创建 Blueprint
            bp = Blueprint("network_previewer", __name__)

            # 获取模板目录
            template_dir = os.path.dirname(os.path.abspath(__file__))

            @bp.route("/")
            def index():
                """主页 - 返回 HTML 模板"""
                return send_from_directory(template_dir, "template.html")

            @bp.route("/api/graph")
            def get_graph():
                """API - 返回图数据"""
                return jsonify({
                    "graph": self._current_graph_data,
                    "title": self._current_title,
                    "options": self._current_options
                })

            # 注册 Blueprint
            register_blueprint = self._plugin_manager.get_method(
                "http_server.register_blueprint"
            )
            result = register_blueprint(blueprint=bp, url_prefix="/network-preview")

            if result["success"]:
                self._blueprint_registered = True
                print("[NetworkPreviewer] Blueprint 注册成功，前缀: /network-preview")

            return result

        except Exception as e:
            error_msg = f"注册 Blueprint 失败: {str(e)}"
            print(f"[NetworkPreviewer] {error_msg}")
            return {"success": False, "error": error_msg}

    def on_unload(self):
        """插件卸载时的清理工作"""
        pass


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
    print("[NetworkPreviewer] 正在加载 Network Previewer 插件...")
    _plugin_instance = NetworkPreviewerPlugin()
    
    # 检查 http_server 插件是否可用
    if not plugin_manager.is_plugin_loaded("http_server"):
        error_msg = "http_server 插件未加载，请先加载 http_server 插件"
        print(f"[NetworkPreviewer] 错误: {error_msg}")
        return {"widget": None, "namespace": "network_previewer", "error": error_msg}

    # 设置 plugin_manager
    _plugin_instance.set_plugin_manager(plugin_manager)

    # 注册暴露的方法到全局域
    plugin_manager.register_method(
        "network_previewer", "view_network", _plugin_instance.view_network
    )

    # 立即注册 Blueprint（服务器已启动）
    result = _plugin_instance._register_blueprint()
    if result["success"]:
        print("[NetworkPreviewer] Blueprint 注册成功")
    else:
        print(f"[NetworkPreviewer] Blueprint 注册失败: {result.get('error')}")

    print("[NetworkPreviewer] Network Previewer 插件加载完成")
    return {"widget": None, "namespace": "network_previewer"}


def unload_plugin(plugin_manager: PluginManager):
    """
    插件卸载回调

    Args:
        plugin_manager: 插件管理器实例
    """
    print("[NetworkPreviewer] 正在卸载 Network Previewer 插件...")
    if _plugin_instance is not None:
        _plugin_instance.on_unload()
    print("[NetworkPreviewer] Network Previewer 插件卸载完成")
