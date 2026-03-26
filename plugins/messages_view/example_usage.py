"""
Messages View Plugin 使用示例

注意：使用此插件前，必须先加载 http_server 插件
"""


# ============================================
# 示例 1: 基本用法
# ============================================

def example_basic_usage(plugin_manager):
    """基本使用示例"""
    
    # 获取 view_messages 方法
    view_messages = plugin_manager.get_method("messages_view.view_messages")
    
    # 准备消息列表
    messages = [
        {"role": "system", "content": "你是一个有用的助手"},
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么我可以帮助你的吗？"}
    ]
    
    # 在浏览器中查看
    result = view_messages(messages, title="简单对话")
    
    if result["success"]:
        print(f"已打开浏览器: {result['url']}")
    else:
        print(f"错误: {result['error']}")


# ============================================
# 示例 2: 带工具调用的对话
# ============================================

def example_with_tool_calls(plugin_manager):
    """带工具调用的对话示例"""
    
    view_messages = plugin_manager.get_method("messages_view.view_messages")
    
    messages = [
        {"role": "system", "content": "你是一个可以查询天气的助手"},
        {"role": "user", "content": "北京今天天气怎么样？"},
        {
            "role": "assistant",
            "content": "我来帮您查询北京的天气",
            "tool_calls": [
                {
                    "id": "call_weather_001",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"city": "北京", "date": "2024-01-15"}'
                    }
                }
            ]
        },
        {
            "role": "tool",
            "tool_call_id": "call_weather_001",
            "content": '{"temperature": 25, "condition": "晴朗", "humidity": "45%"}'
        },
        {"role": "assistant", "content": "北京今天天气晴朗，气温25°C，湿度45%"}
    ]
    
    view_messages(messages, title="天气查询对话")


# ============================================
# 示例 3: 多模态消息（文本+图片）
# ============================================

def example_multimodal(plugin_manager):
    """多模态消息示例"""
    
    view_messages = plugin_manager.get_method("messages_view.view_messages")
    
    messages = [
        {"role": "system", "content": "你可以分析图片内容"},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "描述这张图片中的内容"},
                {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
            ]
        },
        {"role": "assistant", "content": "这张图片展示了一片美丽的风景..."}
    ]
    
    view_messages(messages, title="图片分析对话")


# ============================================
# 示例 4: 带代码的对话
# ============================================

def example_with_code(plugin_manager):
    """带代码的对话示例"""
    
    view_messages = plugin_manager.get_method("messages_view.view_messages")
    
    messages = [
        {"role": "user", "content": "写一个快速排序算法"},
        {
            "role": "assistant",
            "content": """当然可以！以下是 Python 实现的快速排序：

```python
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)

print(quicksort([3, 6, 8, 10, 1, 2, 1]))
```

这个实现使用了分治思想，时间复杂度为 O(n log n)。"""
        }
    ]
    
    view_messages(messages, title="代码示例")


# ============================================
# 快速测试脚本
# ============================================

if __name__ == "__main__":
    """独立测试脚本"""
    import sys
    import os
    import time
    
    # 添加项目根目录到路径
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    # 模拟 plugin_manager
    class MockPluginManager:
        def __init__(self):
            self._methods = {}
            self._plugins = {}
        
        def register_method(self, namespace, name, method):
            self._methods[f"{namespace}.{name}"] = method
        
        def get_method(self, name):
            return self._methods.get(name)
        
        def is_plugin_loaded(self, name):
            return name in self._plugins
        
        def set_plugin_loaded(self, name):
            self._plugins[name] = True
    
    # 加载插件
    from plugins.http_server.main import load_plugin as load_http_server
    from plugins.messages_view.main import load_plugin as load_messages_view
    
    plugin_manager = MockPluginManager()
    
    # 加载 http_server
    load_http_server(plugin_manager)
    plugin_manager.set_plugin_loaded("http_server")
    
    # 加载 messages_view
    result = load_messages_view(plugin_manager)
    if result.get("error"):
        print(f"加载失败: {result['error']}")
        sys.exit(1)
    
    # 创建测试消息
    test_messages = [
        {"role": "system", "content": "你是一个编程助手"},
        {"role": "user", "content": "解释什么是递归"},
        {
            "role": "assistant",
            "content": """# 递归（Recursion）

递归是指函数在执行过程中**调用自身**的编程技巧。

## 核心要素

1. **基准条件**（Base Case）：递归终止的条件
2. **递归条件**（Recursive Case）：继续调用自身的条件

## 经典示例

```python
def factorial(n):
    # 基准条件
    if n <= 1:
        return 1
    # 递归条件
    return n * factorial(n - 1)

print(factorial(5))  # 输出: 120
```

## 优缺点

| 优点 | 缺点 |
|------|------|
| 代码简洁 | 性能开销 |
| 逻辑清晰 | 栈溢出风险 |
| 易于理解 | 调试困难 |

递归是解决许多算法问题的强大工具！"""
        }
    ]
    
    # 启动查看
    print("启动消息查看器...")
    view_messages = plugin_manager.get_method("messages_view.view_messages")
    result = view_messages(test_messages, title="递归解释")
    
    if result["success"]:
        print(f"请在浏览器查看: {result['url']}")
        print("按 Ctrl+C 停止...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_server = plugin_manager.get_method("http_server.stop")
            stop_server()
            print("\n已停止")
    else:
        print(f"错误: {result.get('error')}")
