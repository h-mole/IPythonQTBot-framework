# 邮箱工具插件

## 功能介绍

邮箱工具插件提供了完整的邮件管理功能，包括：

- 📧 多账号管理（支持配置多个邮箱账号）
- 📨 邮件收取（后台线程异步拉取）
- 📄 邮件预览（使用 Qt 富文本控件显示 HTML 邮件）
- 📎 附件管理（查看和下载附件）
- ✉️ 邮件发送（支持 HTML 正文和附件）
- 🔍 邮件列表展示（主题、发件人、日期、预览等）

## 数据格式

### 邮箱账号配置结构

JSON 文件 `email_accounts.json` 包含以下字段：

```json
{
  "accounts": [
    {
      "name": "账号名称",
      "username": "邮箱地址",
      "password": "密码或授权码",
      "imap_server": "IMAP 服务器地址",
      "imap_port": 993,
      "smtp_server": "SMTP 服务器地址",
      "smtp_port": 587,
      "use_ssl": true
    }
  ]
}
```

### 配置字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| name | 账号名称（自定义） | 公司邮箱、个人 Gmail |
| username | 邮箱地址 | your_email@example.com |
| password | 密码或授权码 | your_password_or_app_token |
| imap_server | IMAP 服务器 | imap.gmail.com |
| imap_port | IMAP 端口 | 993 |
| smtp_server | SMTP 服务器 | smtp.gmail.com |
| smtp_port | SMTP 端口 | 587 |
| use_ssl | 是否使用 SSL | true/false |

### 数据存储位置

- 配置文件：`plugins/email_utils/data/email_accounts.json`

## API 接口

其他插件可以通过以下方式调用邮箱管理功能：

```python
# 获取插件管理器
from app_qt.plugin_manager import get_plugin_manager
plugin_manager = get_plugin_manager()

# 获取邮箱管理 API
get_recent_emails = plugin_manager.get_method("email_utils.get_recent_emails")
get_email_detail = plugin_manager.get_method("email_utils.get_email_detail")
send_email = plugin_manager.get_method("email_utils.send_email")
get_attachments = plugin_manager.get_method("email_utils.get_attachments")
download_attachment = plugin_manager.get_method("email_utils.download_attachment")
get_accounts = plugin_manager.get_method("email_utils.get_accounts")

# 示例：获取最近的 20 封邮件
emails = get_recent_emails("我的邮箱", limit=20)

# 示例：获取邮件详情
detail = get_email_detail("我的邮箱", email_id)

# 示例：发送邮件
success = send_email(
    account_name="我的邮箱",
    to="recipient@example.com",
    subject="测试邮件",
    body="<h1>你好</h1><p>这是一封测试邮件</p>",
    attachments=["/path/to/file.pdf"]
)

# 示例：获取附件列表
attachments = get_attachments("我的邮箱", email_id)

# 示例：下载附件
success = download_attachment(
    "我的邮箱",
    email_id,
    "file.pdf",
    "/path/to/save/file.pdf"
)

# 示例：获取所有配置的账号
accounts = get_accounts()
```

## 使用方法

### 1. 配置邮箱账号

#### 方法一：通过界面配置

1. 点击 **"⚙️ 账号配置"** 按钮
2. 点击 **"➕ 添加账号"**
3. 填写邮箱信息：
   - 账号名称：自定义名称（如：公司邮箱、个人 Gmail）
   - 邮箱地址：完整的邮箱地址
   - 密码/授权码：邮箱密码或客户端授权码
   - IMAP 服务器：如 imap.gmail.com
   - IMAP 端口：通常为 993（SSL）
   - SMTP 服务器：如 smtp.gmail.com
   - SMTP 端口：通常为 587 或 465
   - 使用 SSL：勾选以启用加密连接
4. 点击 **"确定"** 保存

#### 方法二：直接编辑配置文件

编辑 `plugins/email_utils/data/email_accounts.json`：

```json
{
  "accounts": [
    {
      "name": "公司邮箱",
      "username": "user@company.com",
      "password": "your_app_password",
      "imap_server": "imap.company.com",
      "imap_port": 993,
      "smtp_server": "smtp.company.com",
      "smtp_port": 587,
      "use_ssl": true
    },
    {
      "name": "个人 Gmail",
      "username": "personal@gmail.com",
      "password": "gmail_app_password",
      "imap_server": "imap.gmail.com",
      "imap_port": 993,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "use_ssl": true
    }
  ]
}
```

### 2. 查看邮件

1. 从下拉列表选择邮箱账号
2. 系统会自动获取最近的 20 封邮件
3. 双击邮件可查看详细内容
4. 在详情对话框中可以：
   - 查看 HTML 格式的邮件正文
   - 查看附件列表
   - 下载附件到本地

### 3. 发送邮件

1. 选择发件人账号
2. 点击 **"📝 写邮件"** 按钮
3. 填写：
   - 收件人：多个收件人用逗号分隔
   - 主题：邮件主题
   - 正文：支持 HTML 格式
   - 附件：可选
4. 点击 **"📨 发送邮件"**

### 4. 刷新邮件

点击 **"🔄 刷新邮件"** 按钮重新获取最新邮件。

## 常见邮箱服务器配置

### Gmail

```json
{
  "imap_server": "imap.gmail.com",
  "imap_port": 993,
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "use_ssl": true
}
```

**注意**：
- 需要开启两步验证
- 需要生成应用专用密码（App Password）

### 163 邮箱

```json
{
  "imap_server": "imap.163.com",
  "imap_port": 993,
  "smtp_server": "smtp.163.com",
  "smtp_port": 465,
  "use_ssl": true
}
```

**注意**：
- 需要在设置中开启 POP3/SMTP/IMAP 服务
- 需要使用客户端授权码（不是登录密码）

### QQ 邮箱

```json
{
  "imap_server": "imap.qq.com",
  "imap_port": 993,
  "smtp_server": "smtp.qq.com",
  "smtp_port": 465,
  "use_ssl": true
}
```

**注意**：
- 需要在设置中开启 IMAP/SMTP 服务
- 需要获取授权码

### Outlook/Hotmail

```json
{
  "imap_server": "outlook.office365.com",
  "imap_port": 993,
  "smtp_server": "smtp.office365.com",
  "smtp_port": 587,
  "use_ssl": true
}
```

### Exchange

```json
{
  "imap_server": "你的 exchange 服务器地址",
  "imap_port": 993,
  "smtp_server": "你的 exchange 服务器地址",
  "smtp_port": 587,
  "use_ssl": true
}
```

## 后台线程机制

邮件获取操作在后台线程中进行，不会阻塞界面：

1. 点击刷新按钮后，显示进度条
2. 创建 `EmailFetchWorker` 线程
3. 在线程中连接 IMAP 服务器并获取邮件
4. 获取完成后通过信号通知主线程更新界面
5. 如果发生错误，显示错误提示

## 邮件正文渲染

使用 Qt 的 `QTextBrowser` 控件渲染 HTML 邮件：

- 支持 HTML 格式
- 支持内联图片
- 支持超链接（可点击打开）
- 如果是纯文本邮件，会自动转换为 HTML 显示

## 附件处理

### 查看附件

在邮件详情对话框中，会显示附件列表，包含：
- 文件名
- 文件大小（自动格式化为 B/KB/MB/GB）

### 下载附件

1. 在附件列表中选择附件
2. 点击 **"⬇️ 下载选中附件"**
3. 选择保存路径
4. 确认保存

## 注意事项

1. **安全性**：
   - 密码保存在本地配置文件中
   - 建议使用客户端授权码而非真实密码
   - 不要分享配置文件

2. **网络连接**：
   - 需要网络连接才能收发邮件
   - 如果网络不通，会显示错误提示

3. **邮箱服务商限制**：
   - 某些邮箱服务商可能限制第三方客户端
   - 部分邮箱需要特殊配置（如开启 IMAP 服务）

4. **大附件**：
   - 下载大附件可能需要较长时间
   - 注意邮箱服务商的附件大小限制

5. **HTML 邮件安全**：
   - 不执行 JavaScript
   - 外部图片可能需要手动加载
   - 注意钓鱼邮件风险

## 依赖

- PySide6：GUI 框架
- imaplib2：IMAP 邮件接收（Python 标准库 imaplib 的增强版）
- beautifulsoup4：HTML 解析
- email：Python 标准库，邮件解析
- smtplib：Python 标准库，邮件发送

## 运行初始化脚本

首次使用前，建议运行初始化脚本创建配置文件：

```bash
cd plugins/email_utils
python init_data.py
```

这会创建示例配置文件，然后根据实际需要进行修改。

## 故障排查

### 无法连接 IMAP 服务器

1. 检查网络连接
2. 检查服务器地址和端口是否正确
3. 检查防火墙设置
4. 确认邮箱服务商是否支持 IMAP

### 登录失败

1. 确认用户名和密码正确
2. 某些邮箱需要使用授权码而非登录密码
3. 确认已开启 IMAP/SMTP 服务
4. 检查是否需要两步验证

### 无法发送邮件

1. 检查 SMTP 服务器配置
2. 确认端口和 SSL 设置正确
3. 某些邮箱服务商限制发送频率
4. 检查附件是否过大

### HTML 邮件显示异常

1. 某些复杂的 HTML 可能无法完全渲染
2. 外部资源（如图片）可能被阻止
3. 尝试切换到纯文本视图
