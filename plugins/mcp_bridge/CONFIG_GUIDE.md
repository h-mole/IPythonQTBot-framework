# MCP Bridge 配置指南

## 🔧 配置文件位置

配置文件位于：
```
~/IPythonQTBot/mcp_bridge/config.json
```

在 Windows 上通常是：
```
C:\Users\你的用户名\IPythonQTBot\mcp_bridge\config.json
```

## 📝 配置示例

### HTTP 流式服务器配置

```json
{
  "mcpServers": {
    "web-search-prime": {
      "type": "streamable-http",
      "url": "https://open.bigmodel.cn/api/mcp/web_search_prime/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_ACTUAL_API_KEY_HERE"
      }
    }
  }
}
```

### stdio 服务器配置

```json
{
  "mcpServers": {
    "local-file-server": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mcp_file_server"],
      "env": {
        "API_KEY": "your_api_key",
        "ROOT_DIR": "/path/to/files"
      }
    }
  }
}
```

## 🔑 获取 API Key

### 智谱 AI (Zhipu)

1. 访问 [智谱 AI 开放平台](https://open.bigmodel.cn/)
2. 注册/登录账号
3. 进入「控制台」→「API 密钥管理」
4. 创建新的 API Key
5. 复制 API Key 到配置文件中

### 其他提供商

请参考对应平台的文档获取 API Key。

## ⚠️ 常见错误及解决方法

### 1. 401 认证错误

**错误信息**:
```
{'code': 401, 'msg': '令牌无效或已过期', 'success': False}
```

**原因**:
- API Key 配置错误
- API Key 已过期
- Authorization 格式不正确

**解决方法**:

1. **检查 API Key 是否正确**
   ```json
   {
     "headers": {
       "Authorization": "Bearer sk-xxxxxxxxxxxxx"
     }
   }
   ```
   
2. **确认 Bearer 后面有空格**
   ```
   ✅ 正确：Bearer sk-xxxxx
   ❌ 错误：Bearer sk-xxxxx (缺少空格)
   ```

3. **检查 API Key 是否有效**
   - 登录对应的开放平台
   - 验证 API Key 状态是否正常
   - 如有必要，重新生成 API Key

4. **从环境变量读取（推荐）**
   ```json
   {
     "mcpServers": {
       "web-search-prime": {
         "type": "streamable-http",
         "url": "https://open.bigmodel.cn/api/mcp/web_search_prime/mcp",
         "headers": {
           "Authorization": "Bearer ${ZHIPU_API_KEY}"
         }
       }
     }
   }
   ```
   
   然后设置环境变量：
   ```bash
   # Windows PowerShell
   $env:ZHIPU_API_KEY="sk-xxxxxxxxxxxxx"
   
   # Linux/Mac
   export ZHIPU_API_KEY="sk-xxxxxxxxxxxxx"
   ```

### 2. 配置文件不存在

**错误信息**:
```
[MCP Bridge] 配置文件不存在，请创建：...
```

**解决方法**:
首次运行时会自动创建示例配置文件。如果未创建，可以手动创建：

```bash
# 创建配置目录
mkdir -p $HOME\IPythonQTBot\mcp_bridge

# 复制示例配置
copy plugins\mcp_bridge\config.example.json $HOME\IPythonQTBot\mcp_bridge\config.json
```

然后编辑配置文件，填入正确的 API Key。

### 3. JSON 格式错误

**错误信息**:
```
JSONDecodeError: Expecting property name enclosed in double quotes...
```

**原因**: JSON 格式不正确

**解决方法**:
使用 JSON 验证工具检查配置文件，确保：
- 所有键名用双引号
- 逗号分隔正确
- 括号匹配

**正确示例**:
```json
{
  "mcpServers": {
    "server-1": {
      "type": "streamable-http",
      "url": "https://example.com/mcp"
    }
  }
}
```

**错误示例**:
```json
{
  mcpServers: {  // ❌ 键名缺少引号
    "server-1": {
      "type": "streamable-http",
      "url": "https://example.com/mcp",  // ✅ 正确
    }  // ❌ 最后一个元素后面不应该有逗号
  }
}
```

### 4. URL 配置错误

**错误信息**:
```
[MCP Bridge] URL 未配置：server-name
```

**解决方法**:
确保配置了完整的 URL：

```json
{
  "mcpServers": {
    "my-server": {
      "type": "streamable-http",
      "url": "https://api.example.com/mcp/v1"
    }
  }
}
```

## 🧪 测试配置

### 方法 1: 运行测试脚本

```bash
python plugins/mcp_bridge/test_mcp_bridge.py
```

查看输出：
- ✅ `已连接到服务器：xxx，共 X 个工具` - 配置正确
- ❌ `连接服务器失败` - 检查错误信息

### 方法 2: 在 IPython 中测试

```python
from app_qt.plugin_manager import get_plugin_manager

pm = get_plugin_manager()
pm.load_plugin("mcp_bridge")

# 查看已配置的服务器
servers = pm.get_method("mcp_bridge.list_servers")()
print(f"已配置服务器：{servers}")

# 等待连接完成
import time
time.sleep(3)

# 查看已连接的服务器
connected = pm.get_method("mcp_bridge.list_connected_servers")()
print(f"已连接的服务器：{connected}")

# 获取工具列表
tools = pm.get_method("mcp_bridge.get_mcp_tools")()
print(f"可用工具数量：{len(tools)}")
```

## 🔐 安全建议

### 1. 不要提交配置文件到 Git

配置文件已添加到 `.gitignore`：
```
# .gitignore
config.json
*.local.json
```

### 2. 使用环境变量

推荐通过环境变量管理敏感信息：

```bash
# Windows PowerShell
[Environment]::SetEnvironmentVariable("ZHIPU_API_KEY", "sk-xxxxx", "User")

# Linux/Mac
export ZHIPU_API_KEY="sk-xxxxx"
```

然后在配置文件中引用：
```json
{
  "headers": {
    "Authorization": "Bearer ${ZHIPU_API_KEY}"
  }
}
```

### 3. 定期更新 API Key

建议每 3-6 个月更新一次 API Key。

## 📚 完整配置示例

```json
{
  "mcpServers": {
    "zhipu-search": {
      "type": "streamable-http",
      "url": "https://open.bigmodel.cn/api/mcp/web_search_prime/mcp",
      "headers": {
        "Authorization": "Bearer sk-your-api-key-here"
      }
    },
    "local-files": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mcp_file_server", "--root", "C:\\Users\\Public"],
      "env": {
        "DEBUG": "false"
      }
    },
    "database-query": {
      "type": "stdio",
      "command": "node",
      "args": ["mcp-db-server.js"],
      "env": {
        "DATABASE_URL": "postgresql://user:pass@localhost/dbname"
      }
    }
  }
}
```

## 🆘 获取帮助

如果遇到问题：

1. 查看详细错误日志
2. 检查配置文件格式
3. 验证 API Key 有效性
4. 查看 [README.md](README.md) 故障排查章节
5. 查看 [FIX_RECORD.md](FIX_RECORD.md) 问题修复记录

---

**最后更新**: 2026-03-21  
**版本**: v1.0.1
