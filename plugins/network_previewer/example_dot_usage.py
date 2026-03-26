"""
Network Previewer 插件 - 从 DOT 文件加载示例

本示例演示如何从 DOT 文件读取并可视化
"""

import networkx as nx


def load_dot_and_view(dot_file_path, plugin_manager, title="Network View"):
    """
    从 DOT 文件加载并显示网络图
    
    Args:
        dot_file_path: DOT 文件路径
        plugin_manager: 插件管理器实例
        title: 页面标题
    """
    # 使用 pydot 读取 DOT 文件
    try:
        from networkx.drawing.nx_pydot import read_dot
        
        # 读取 DOT 文件
        G = read_dot(dot_file_path)
        
        # 转换节点 ID 为字符串（DOT 读取的 ID 可能有引号）
        G = nx.convert_node_labels_to_integers(G, label_attribute='original_label')
        
        # 获取 network_previewer 插件方法
        view_network = plugin_manager.get_method("network_previewer.view_network")
        
        # 显示网络图
        result = view_network(G, title=title)
        return result
        
    except ImportError:
        print("请先安装 pydot: pip install pydot")
        return None
    except Exception as e:
        print(f"加载 DOT 文件失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def load_dot_with_pydot(dot_file_path):
    """
    使用 pydot 读取 DOT 文件并转换为 NetworkX 图
    保留颜色等属性
    """
    import pydot
    
    # 读取 DOT 文件
    graphs = pydot.graph_from_dot_file(dot_file_path)
    if not graphs:
        raise ValueError(f"无法解析 DOT 文件: {dot_file_path}")
    
    dot_graph = graphs[0]
    
    # 创建 NetworkX 图
    if dot_graph.get_type() == 'digraph':
        G = nx.DiGraph()
    else:
        G = nx.Graph()
    
    # 添加节点
    for node in dot_graph.get_nodes():
        node_name = node.get_name().strip('"')
        if node_name in ['node', 'edge', 'graph']:
            continue
            
        # 获取节点属性
        attrs = {}
        if node.get_label():
            attrs['label'] = node.get_label().strip('"')
        if node.get_fillcolor():
            attrs['fillcolor'] = node.get_fillcolor().strip('"')
        if node.get_color():
            attrs['color'] = node.get_color().strip('"')
        if node.get_shape():
            attrs['shape'] = node.get_shape().strip('"')
        if node.get_style():
            attrs['style'] = node.get_style().strip('"')
        if node.get_tooltip():
            attrs['title'] = node.get_tooltip().strip('"')
        if node.get_fontcolor():
            attrs['fontcolor'] = node.get_fontcolor().strip('"')
        
        G.add_node(node_name, **attrs)
    
    # 添加边
    for edge in dot_graph.get_edges():
        source = edge.get_source().strip('"')
        target = edge.get_destination().strip('"')
        
        # 获取边属性
        attrs = {}
        if edge.get_label():
            attrs['label'] = edge.get_label().strip('"')
        if edge.get_color():
            attrs['color'] = edge.get_color().strip('"')
        if edge.get_style():
            attrs['style'] = edge.get_style().strip('"')
        if edge.get_penwidth():
            try:
                attrs['value'] = float(edge.get_penwidth())
            except:
                pass
        
        G.add_edge(source, target, **attrs)
    
    return G


# 使用示例
if __name__ == "__main__":
    print("""
从 DOT 文件加载并显示网络图的示例:

方法1: 使用 pydot 读取（推荐，保留颜色属性）
    from plugins.network_previewer.example_dot_usage import load_dot_with_pydot
    
    # 加载 DOT 文件
    G = load_dot_with_pydot("project_deps.dot")
    
    # 获取插件方法并显示
    view_network = plugin_manager.get_method("network_previewer.view_network")
    view_network(G, title="项目依赖图")

方法2: 直接使用 NetworkX 的 read_dot
    from networkx.drawing.nx_pydot import read_dot
    
    G = read_dot("project_deps.dot")
    view_network = plugin_manager.get_method("network_previewer.view_network")
    view_network(G, title="项目依赖图")
""")
