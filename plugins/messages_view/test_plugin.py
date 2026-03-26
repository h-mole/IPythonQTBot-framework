"""
Messages View Plugin 测试脚本

注意：运行此测试前，确保 http_server 插件已加载
"""

import sys
import os
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def test_plugin():
    """测试插件功能"""
    
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
    
    # 导入并加载 http_server 插件（会自动启动服务器）
    from plugins.http_server.main import load_plugin as load_http_server
    
    plugin_manager = MockPluginManager()
    result = load_http_server(plugin_manager)
    plugin_manager.set_plugin_loaded("http_server")
    
    # 检查服务器是否启动成功
    is_running = plugin_manager.get_method("http_server.is_running")
    if not is_running():
        print("[ERROR] HTTP 服务器启动失败")
        return
    
    get_url = plugin_manager.get_method("http_server.get_url")
    print(f"[OK] HTTP 服务器运行中: {get_url()}")
    
    # 导入并加载 messages_view 插件（会自动注册 Blueprint）
    from plugins.messages_view.main import load_plugin as load_messages_view
    
    result = load_messages_view(plugin_manager)
    if result.get("error"):
        print(f"加载失败: {result['error']}")
        return
    
    # 获取 view_messages 方法
    view_messages = plugin_manager.get_method("messages_view.view_messages")
    
    # 测试消息数据
    test_messages = [
        {
            "role": "system",
            "content": "你是一个有用的 AI 助手，可以帮助用户解决各种问题。"
        },
        {
            "role": "user",
            "content": "你好，请介绍一下自己"
        },
        {
            "role": "assistant",
            "content": "你好！我是 Claude，一个 AI 助手。我可以帮你：\n\n- 回答问题\n- 编写代码\n- 分析数据\n- 创作内容\n\n有什么我可以帮助你的吗？"
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "描述这张图片"},
                {"type": "image_url", "image_url": {"url": "https://picsum.photos/400/300"}}
            ]
        },
        {
            "role": "assistant",
            "content": "我来帮您查询天气信息",
            "tool_calls": [
                {
                    "id": "call_123abc",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"city": "北京", "date": "2024-01-15"}'
                    }
                },
                {
                    "id": "call_456def",
                    "type": "function",
                    "function": {
                        "name": "get_temperature",
                        "arguments": '{"location": "上海"}'
                    }
                }
            ]
        },
        {
            "role": "tool",
            "tool_call_id": "call_123abc",
            "content": '{"temperature": 25, "condition": "晴朗", "humidity": "45%"}'
        },
        {
            "role": "assistant",
            "content": "根据查询结果，北京今天天气**晴朗**，气温 **25°C**，湿度 45%。这是一个非常适合户外活动的好天气！"
        },
        {
            "role": "user",
            "content": "帮我写一段 Python 代码计算斐波那契数列"
        },
        {
            "role": "assistant",
            "content": '''当然可以！以下是计算斐波那契数列的 Python 代码：

```python
def fibonacci(n):
    """计算斐波那契数列的前 n 项"""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib

# 示例：计算前 10 项
n = 10
result = fibonacci(n)
print(f"斐波那契数列前 {n} 项: {result}")
```

**输出结果：**
```
斐波那契数列前 10 项: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
```

这段代码使用迭代方式计算，时间复杂度为 O(n)，空间复杂度为 O(n)。'''
        }
    ]
    
    print("=" * 60)
    print("Messages View Plugin 测试")
    print("=" * 60)
    
    # 测试 view_messages
    print("\n1. 测试 view_messages 方法...")
    result = view_messages(test_messages, title="测试对话 - 完整功能展示")
    
    if result["success"]:
        print(f"[OK] 成功！请在浏览器中查看: {result['url']}")
        print(f"   消息数量: {result['message_count']}")
    else:
        print(f"[ERROR] 失败: {result.get('error', '未知错误')}")
        return
    
    # 保持服务器运行一段时间
    print("\n2. 服务器运行中...")
    print("   按 Ctrl+C 停止测试")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n3. 停止服务器...")
        stop_server = plugin_manager.get_method("http_server.stop")
        result = stop_server()
        print(f"[OK] {result['message']}")
    
    print("\n测试完成！")


if __name__ == "__main__":
    test_plugin()
