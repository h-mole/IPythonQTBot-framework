"""
Network Previewer 插件测试
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def test_import():
    """测试插件是否能正常导入"""
    try:
        from plugins.network_previewer.main import NetworkPreviewerPlugin, load_plugin, unload_plugin
        print("[OK] 插件导入成功")
        return True
    except Exception as e:
        print(f"[FAIL] 插件导入失败: {e}")
        return False


def test_graph_conversion():
    """测试图数据转换"""
    try:
        import networkx as nx
        from plugins.network_previewer.main import NetworkPreviewerPlugin
        
        plugin = NetworkPreviewerPlugin()
        
        # 创建测试图
        G = nx.Graph()
        G.add_node("A", label="节点 A", group="g1")
        G.add_node("B", label="节点 B", group="g1")
        G.add_node("C", label="节点 C", group="g2")
        G.add_edge("A", "B", label="边 AB", value=3)
        G.add_edge("B", "C", label="边 BC", value=2)
        
        # 转换图数据
        data = plugin._convert_graph(G)
        
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 3
        assert len(data["edges"]) == 2
        
        # 验证节点属性
        node_a = next(n for n in data["nodes"] if n["id"] == "A")
        assert node_a["label"] == "节点 A"
        assert node_a["group"] == "g1"
        
        # 验证边属性
        edge_ab = next(e for e in data["edges"] if e["from"] == "A" and e["to"] == "B")
        assert edge_ab["label"] == "边 AB"
        assert edge_ab["value"] == 3
        
        print("[OK] 图数据转换测试通过")
        return True
        
    except Exception as e:
        print(f"[FAIL] 图数据转换测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_directed_graph():
    """测试有向图转换"""
    try:
        import networkx as nx
        from plugins.network_previewer.main import NetworkPreviewerPlugin
        
        plugin = NetworkPreviewerPlugin()
        
        # 创建有向图
        G = nx.DiGraph()
        G.add_node("start", label="开始")
        G.add_node("end", label="结束")
        G.add_edge("start", "end")
        
        # 转换图数据
        data = plugin._convert_graph(G)
        
        # 验证边有箭头
        edge = data["edges"][0]
        assert edge["arrows"] == "to"
        
        print("[OK] 有向图转换测试通过")
        return True
        
    except Exception as e:
        print(f"[FAIL] 有向图转换测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_template_html_exists():
    """测试 HTML 模板文件是否存在"""
    try:
        template_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "template.html"
        )
        assert os.path.exists(template_path), f"模板文件不存在: {template_path}"
        
        # 检查是否包含 vis-network CDN
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'vis-network' in content, "模板缺少 vis-network 引用"
            assert 'bootcdn' in content, "模板应使用 BootCDN"
        
        print("[OK] HTML 模板文件检查通过")
        return True
        
    except Exception as e:
        print(f"[FAIL] HTML 模板文件检查失败: {e}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("Network Previewer 插件测试")
    print("=" * 50)
    
    tests = [
        ("导入测试", test_import),
        ("图转换测试", test_graph_conversion),
        ("有向图测试", test_directed_graph),
        ("模板文件测试", test_template_html_exists),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n[{name}]")
        results.append(test_func())
    
    print("\n" + "=" * 50)
    print(f"测试结果: {sum(results)}/{len(results)} 通过")
    print("=" * 50)
    
    return all(results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
