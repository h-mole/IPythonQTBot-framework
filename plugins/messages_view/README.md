# Messages View Plugin

OpenAI Messages 可视化插件，用于在浏览器中展示 OpenAI API 的消息内容。

**注意：此插件依赖 http_server 插件，请先确保 http_server 已加载。**

## 依赖

- `plugin:http_server` - Flask HTTP 服务器插件

## 功能特性

- ✅ 支持多种消息类型（text, image_url, tool_calls, tool_result）
- ✅ 支持多模态内容展示（文本 + 图片）
- ✅ 工具调用面板可折叠展开
- ✅ 代码块语法高亮
- ✅ Markdown 渲染支持
- ✅ 自动打开系统浏览器
- ✅ 简洁美观的界面设计
- ✅ **插件加载时自动注册路由**

## 支持的消息格式

### 1. 普通文本消息
```python
{
    "role": "user",
    "content": "你好，请介绍一下自己"
}
```

### 2. 带图片的消息
```python
{
    "role": "user",
    "content": [
        {"type": "text", "text": "描述这张图片"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
    ]
}
```

### 3. 助手带工具调用的消息
```python
{
    "role": "assistant",
    "content": "我来帮您查询天气",
    "tool_calls": [
        {
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": '{"city": "北京"}'
            }
        }
    ]
}
```

### 4. 工具返回结果消息
```python
{
    "role": "tool",
    "tool_call_id": "call_123",
    "content": '{"temperature": 25, "condition": "晴朗"}'
}
```

## 使用方法

### 基本用法

```python
# 插件加载时会自动注册路由，无需额外配置
# 只需要调用 view_messages 即可在浏览器中查看消息

view_messages = plugin_manager.get_method("messages_view.view_messages")

messages = [
    {"role": "system", "content": "你是一个有用的助手"},
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！有什么我可以帮助你的吗？"}
]

result = view_messages(messages, title="我的对话")
if result["success"]:
    print(f"已打开浏览器: {result['url']}")  # http://127.0.0.1:xxxx/messages-view/
else:
    print(f"错误: {result['error']}")
```

### 完整示例

```python
# 准备消息列表（包含各种类型）
messages = [
    {"role": "system", "content": "你是一个天气助手"},
    {"role": "user", "content": "北京天气怎么样？"},
    {
        "role": "assistant",
        "content": "我来查询一下",
        "tool_calls": [{
            "id": "call_1",
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"city": "北京"}'}
        }]
    },
    {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": '{"temp": 25, "weather": "晴朗"}'
    },
    {"role": "assistant", "content": "北京今天天气晴朗，25°C"}
]

# 在浏览器中查看
view_messages(messages, title="天气查询")
```

## API 接口

### view_messages

在浏览器中展示 messages 列表。

```python
result = plugin_manager.get_method("messages_view.view_messages")(
    messages=[
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there!"}
    ],
    title="对话预览"  # 可选，页面标题
)

if result["success"]:
    print(f"URL: {result['url']}")
    print(f"消息数: {result['message_count']}")
else:
    print(f"错误: {result['error']}")
```

## 技术细节

- 使用 Flask 作为 HTTP 服务器（由 http_server 插件提供）
- **插件加载时自动注册 Blueprint**，URL 前缀为 `/messages-view`
- 前端使用原生 HTML + CSS + JavaScript
- CDN 资源来自 BootCDN

## 路由说明

插件注册后会提供以下路由：

- `GET /messages-view/` - 主页面（HTML 模板）
- `GET /messages-view/api/messages` - 消息数据 API（JSON）
