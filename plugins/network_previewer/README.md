# Network Previewer 插件

NetworkX 网络可视化插件 - 在浏览器中使用 vis-network 可视化展示 NetworkX 图。

## 功能特性

- 🌐 基于 vis-network 的交互式网络可视化
- 📊 支持无向图、有向图、加权图
- 🎨 自动分组着色，支持自定义颜色
- 🔍 缩放、平移、适应窗口等交互功能
- 🔎 节点搜索功能
- ℹ️ 点击节点查看详细信息
- ⚡ 可切换物理引擎，支持层级布局
- 📱 响应式设计

## 依赖

- `http_server` 插件（必须）
- `networkx` Python 包

## 安装

1. 确保已加载 `http_server` 插件
2. 将本插件文件夹复制到 `plugins/` 目录下
3. 重启应用或动态加载插件

## 使用方法

### 基础用法

```python
import networkx as nx
from app_qt.plugin_manager import PluginManager

# 创建 NetworkX 图
G = nx.Graph()
G.add_node("A", label="节点 A", group="group1")
G.add_node("B", label="节点 B", group="group1")
G.add_node("C", label="节点 C", group="group2")
G.add_edge("A", "B", label="边 AB")
G.add_edge("B", "C", label="边 BC")

# 获取插件方法并显示
view_network = plugin_manager.get_method("network_previewer.view_network")
view_network(G, title="我的网络图")
```

### 有向图示例

```python
G = nx.DiGraph()
G.add_node("start", label="开始", color="#4CAF50")
G.add_node("end", label="结束", color="#F44336")
G.add_edge("start", "end", label="流程")

view_network(G, title="流程图")
```

### 带自定义选项

```python
# 层级布局（适合树形结构）
options = {
    "layout": {
        "hierarchical": {
            "enabled": True,
            "direction": "UD",  # 从上到下
            "sortMethod": "directed"
        }
    },
    "physics": {
        "enabled": False
    }
}

view_network(G, title="树形结构", options=options)
```

## 支持的节点属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `label` | str | 节点显示标签 |
| `group` | str | 节点分组（自动分配颜色）|
| `value` | number | 节点大小 |
| `color` | str/dict | 节点颜色 |
| `shape` | str | 节点形状：dot, box, diamond, star, triangle 等 |
| `title` | str | 悬停提示文本 |
| `image` | str | 图片URL（需配合 shape="image"）|

## 支持的边属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `label` | str | 边标签 |
| `value` | number | 边粗细 |
| `color` | str/dict | 边颜色 |
| `title` | str | 悬停提示文本 |
| `dashes` | bool | 是否虚线 |
| `arrows` | str | 箭头方向：to, from, middle, false |

## 界面功能

- **适应窗口**: 自动调整视图以适应所有节点
- **重置**: 重置缩放级别为 1
- **物理引擎**: 切换物理模拟的开启/关闭
- **稳定**: 停止物理模拟并稳定布局
- **搜索**: 按标签或 ID 搜索节点，回车定位
- **节点点击**: 查看节点详细信息
- **鼠标滚轮**: 缩放
- **拖拽**: 平移视图

## 配置选项

完整的 vis-network 配置选项请参考：
https://visjs.github.io/vis-network/docs/network/

## 示例文件

查看 `example_usage.py` 获取更多使用示例：
- 基础无向图
- 有向流程图
- 社交网络
- 树形结构

## 技术栈

- 前端: vis-network (BootCDN)
- 后端: Flask Blueprint
- 数据: NetworkX
