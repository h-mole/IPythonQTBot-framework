"""
Network Previewer 插件使用示例

本示例演示如何使用 network_previewer 插件可视化 NetworkX 图
"""

import networkx as nx


def example_basic_graph():
    """示例1：基础无向图"""
    # 创建一个简单的无向图
    G = nx.Graph()
    
    # 添加节点
    G.add_node("A", label="节点 A", group="group1")
    G.add_node("B", label="节点 B", group="group1")
    G.add_node("C", label="节点 C", group="group2")
    G.add_node("D", label="节点 D", group="group2")
    G.add_node("E", label="节点 E", group="group3")
    
    # 添加边
    G.add_edge("A", "B", label="边 AB")
    G.add_edge("B", "C", label="边 BC")
    G.add_edge("C", "D", label="边 CD")
    G.add_edge("D", "E", label="边 DE")
    G.add_edge("E", "A", label="边 EA")
    
    return G


def example_directed_graph():
    """示例2：有向图"""
    # 创建有向图
    G = nx.DiGraph()
    
    # 添加节点（带有更多属性）
    G.add_node("start", label="开始", group="start", value=30, color="#4CAF50")
    G.add_node("process1", label="处理 1", group="process", value=20)
    G.add_node("process2", label="处理 2", group="process", value=20)
    G.add_node("decision", label="决策", group="decision", value=25, shape="diamond")
    G.add_node("end1", label="结束 A", group="end", value=15, color="#F44336")
    G.add_node("end2", label="结束 B", group="end", value=15, color="#F44336")
    
    # 添加带权重的边
    G.add_edge("start", "process1", label="开始", value=2)
    G.add_edge("start", "process2", label="开始", value=2)
    G.add_edge("process1", "decision", label="处理完成", value=1)
    G.add_edge("process2", "decision", label="处理完成", value=1)
    G.add_edge("decision", "end1", label="条件 A", value=1, color="#F44336")
    G.add_edge("decision", "end2", label="条件 B", value=1, color="#2196F3")
    
    return G


def example_weighted_graph():
    """示例3：加权网络（社交网络示例）"""
    G = nx.Graph()
    
    # 人物节点
    people = [
        ("Alice", {"group": "team1", "value": 30}),
        ("Bob", {"group": "team1", "value": 25}),
        ("Carol", {"group": "team1", "value": 20}),
        ("David", {"group": "team2", "value": 28}),
        ("Eve", {"group": "team2", "value": 22}),
        ("Frank", {"group": "team2", "value": 18}),
        ("Grace", {"group": "manager", "value": 35, "shape": "box"}),
    ]
    
    for name, attrs in people:
        G.add_node(name, label=name, **attrs)
    
    # 关系边（权重表示互动频率）
    relationships = [
        ("Alice", "Bob", 5),
        ("Alice", "Carol", 3),
        ("Bob", "Carol", 4),
        ("David", "Eve", 6),
        ("David", "Frank", 2),
        ("Eve", "Frank", 3),
        ("Alice", "David", 2),
        ("Grace", "Alice", 4),
        ("Grace", "David", 4),
        ("Grace", "Bob", 3),
    ]
    
    for u, v, w in relationships:
        G.add_edge(u, v, value=w, title=f"互动频率: {w}")
    
    return G


def example_tree_structure():
    """示例4：树形结构"""
    G = nx.DiGraph()
    
    # 创建树形结构
    nodes = [
        ("root", {"label": "根节点", "group": "root", "value": 40}),
        ("child1", {"label": "子节点 1", "group": "level1", "value": 25}),
        ("child2", {"label": "子节点 2", "group": "level1", "value": 25}),
        ("child3", {"label": "子节点 3", "group": "level1", "value": 25}),
        ("leaf1", {"label": "叶子 1", "group": "level2", "value": 15}),
        ("leaf2", {"label": "叶子 2", "group": "level2", "value": 15}),
        ("leaf3", {"label": "叶子 3", "group": "level2", "value": 15}),
        ("leaf4", {"label": "叶子 4", "group": "level2", "value": 15}),
        ("leaf5", {"label": "叶子 5", "group": "level2", "value": 15}),
    ]
    
    for node_id, attrs in nodes:
        G.add_node(node_id, **attrs)
    
    # 添加层级边
    edges = [
        ("root", "child1"),
        ("root", "child2"),
        ("root", "child3"),
        ("child1", "leaf1"),
        ("child1", "leaf2"),
        ("child2", "leaf3"),
        ("child2", "leaf4"),
        ("child3", "leaf5"),
    ]
    
    for u, v in edges:
        G.add_edge(u, v)
    
    return G


def view_graph_example(plugin_manager):
    """
    使用插件查看图的示例
    
    Args:
        plugin_manager: 插件管理器实例
    """
    # 获取 network_previewer 插件的 view_network 方法
    view_network = plugin_manager.get_method("network_previewer.view_network")
    
    # 示例1：基础图
    G1 = example_basic_graph()
    view_network(G1, title="基础无向图示例")
    
    # 示例2：有向图
    G2 = example_directed_graph()
    view_network(G2, title="有向流程图示例")
    
    # 示例3：社交网络
    G3 = example_weighted_graph()
    view_network(G3, title="社交网络示例")
    
    # 示例4：树形结构（带自定义选项）
    G4 = example_tree_structure()
    custom_options = {
        "layout": {
            "hierarchical": {
                "enabled": True,
                "direction": "UD",  # 从上到下
                "sortMethod": "directed"
            }
        },
        "physics": {
            "enabled": False  # 禁用物理引擎，使用层级布局
        }
    }
    view_network(G4, title="树形结构示例", options=custom_options)


# 如果直接运行此文件，打印使用说明
if __name__ == "__main__":
    print("""
Network Previewer 插件使用示例
==============================

请先确保已加载 http_server 和 network_previewer 插件。

使用方式:
    from app_qt.plugin_manager import PluginManager
    import networkx as nx
    
    # 创建图
    G = nx.Graph()
    G.add_node("A", label="节点 A", group="group1")
    G.add_node("B", label="节点 B", group="group1")
    G.add_edge("A", "B", label="连接")
    
    # 获取插件方法并显示
    view_network = plugin_manager.get_method("network_previewer.view_network")
    view_network(G, title="我的网络图")

支持的节点属性:
    - label: 节点显示标签
    - group: 节点分组（用于自动着色）
    - value: 节点大小
    - color: 节点颜色
    - shape: 节点形状 (dot, box, diamond, star, triangle, etc.)
    - title: 悬停提示文本
    - image: 图片URL（配合 shape="image"）

支持的边属性:
    - label: 边标签
    - value: 边粗细
    - color: 边颜色
    - title: 悬停提示文本
    - dashes: 是否虚线 (true/false)
    - arrows: 箭头方向 (to, from, middle, false)
    
更多 vis-network 配置选项:
    https://visjs.github.io/vis-network/docs/network/
""")
