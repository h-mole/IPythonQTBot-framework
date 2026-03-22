# MCP Bridge 快速入门

## 1. 配置 MCP 服务器

首次运行插件时会自动创建配置文件模板，位置在：
```
~/IPythonQTBot/mcp_bridge/config.json
```

编辑该文件，添加你的 MCP 服务器配置：

```json
{
  "mcpServers": {
    "web-search-prime": {
      "type": "streamable-http",
      "url": "https://open.bigmodel.cn/api/mcp/web_search_prime/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

## 2. 启用外部MCP

IPython 启动时自动加载

## 3. 验证安装

在IPython中执行:

```python
In [1]: agent.show_tools()

[Agent] 可用工具：
1. call_daily_tasks__get_tasks:
API: 获取任务列表
2. call_daily_tasks__get_todo_tasks:
API: 获取状态非“完成”的任务列表
3. call_email_utils__get_recent_emails:
API: 获取最近的邮件列表
4. call_email_utils__send_email:
API: 发送邮件
5. call_email_utils__get_accounts:
API: 获取所有配置的邮箱账号
```

## 4. 启用和禁用能力

点击IPython面板中的"MCP工具设置", 可在弹出的对话框中启用/禁用能力
