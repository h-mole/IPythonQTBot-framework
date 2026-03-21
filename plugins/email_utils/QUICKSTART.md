# 邮箱工具插件快速开始

## 安装依赖

确保已安装以下依赖：

```bash
pip install beautifulsoup4
```

其他依赖（imaplib2, email, smtplib）都是 Python 标准库，无需额外安装。

## 快速配置

### 方法一：运行初始化脚本（推荐）

```bash
cd plugins/email_utils
python init_data.py
```

这会创建示例配置文件 `data/email_accounts.json`。

### 方法二：手动创建配置文件

在 `plugins/email_utils/data/` 目录下创建 `email_accounts.json`：

```json
{
  "accounts": [
    {
      "name": "我的 QQ 邮箱",
      "username": "123456789@qq.com",
      "password": "your_auth_code_here",
      "imap_server": "imap.qq.com",
      "imap_port": 993,
      "smtp_server": "smtp.qq.com",
      "smtp_port": 465,
      "use_ssl": true
    }
  ]
}
```

## 配置您的邮箱

编辑 `data/email_accounts.json`，根据您的邮箱服务商填写正确的信息：

### QQ 邮箱示例

```json
{
  "accounts": [{
    "name": "QQ 邮箱",
    "username": "your_qq@qq.com",
    "password": "your_auth_code",
    "imap_server": "imap.qq.com",
    "imap_port": 993,
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "use_ssl": true
  }]
}
```

**获取授权码步骤：**
1. 登录 QQ 邮箱网页版
2. 设置 → 账户
3. 开启 IMAP/SMTP 服务
4. 发送短信验证
5. 获取授权码

### 163 邮箱示例

```json
{
  "accounts": [{
    "name": "163 邮箱",
    "username": "your_name@163.com",
    "password": "your_auth_code",
    "imap_server": "imap.163.com",
    "imap_port": 993,
    "smtp_server": "smtp.163.com",
    "smtp_port": 465,
    "use_ssl": true
  }]
}
```

### Gmail 示例

```json
{
  "accounts": [{
    "name": "Gmail",
    "username": "your_email@gmail.com",
    "password": "your_app_password",
    "imap_server": "imap.gmail.com",
    "imap_port": 993,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "use_ssl": true
  }]
}
```

**注意：** Gmail 需要：
1. 开启两步验证
2. 生成应用专用密码（App Password）

## 启动主程序

配置完成后，运行主程序：

```bash
python run_helper_qt.py
```

在主界面中，您会看到 **"📧 邮箱管理"** 标签页。

## 基本使用

### 查看邮件

1. 从下拉列表选择邮箱账号
2. 系统会自动获取最近的 20 封邮件
3. 双击邮件查看详情

### 发送邮件

1. 点击 **"📝 写邮件"**
2. 填写收件人、主题、正文
3. 可添加附件
4. 点击 **"📨 发送邮件"**

### 下载附件

1. 双击有附件的邮件（附件列显示📎图标）
2. 在详情对话框中选择附件
3. 点击 **"⬇️ 下载选中附件"**
4. 选择保存位置

## API 调用示例

在其他插件中使用邮箱功能：

```python
from app_qt.plugin_manager import get_plugin_manager

plugin_manager = get_plugin_manager()

# 获取最近邮件
get_emails = plugin_manager.get_method("email_utils.get_recent_emails")
emails = get_emails("我的 QQ 邮箱", limit=10)

# 获取邮件详情
get_detail = plugin_manager.get_method("email_utils.get_email_detail")
detail = get_detail("我的 QQ 邮箱", email_id)

# 发送邮件
send_email = plugin_manager.get_method("email_utils.send_email")
success = send_email(
    account_name="我的 QQ 邮箱",
    to="recipient@example.com",
    subject="测试",
    body="<h1>你好</h1>",
    attachments=[]
)

# 获取所有账号
get_accounts = plugin_manager.get_method("email_utils.get_accounts")
accounts = get_accounts()
```

## 故障排查

### 问题：无法连接服务器

**解决：**
- 检查网络连接
- 确认 IMAP/SMTP 服务器地址和端口正确
- 检查防火墙设置

### 问题：登录失败

**解决：**
- 确认使用了正确的授权码（不是登录密码）
- 确认已开启 IMAP/SMTP 服务
- 检查是否需要两步验证

### 问题：找不到配置文件

**解决：**
- 运行 `python init_data.py` 创建示例配置
- 确认文件位于 `plugins/email_utils/data/email_accounts.json`

## 安全提示

1. **保护配置文件**：包含邮箱密码/授权码，不要分享给他人
2. **使用授权码**：建议使用邮箱服务商提供的授权码，而非真实密码
3. **定期更新密码**：定期更改邮箱密码和授权码
4. **注意钓鱼邮件**：谨慎处理陌生邮件中的链接

## 更多帮助

详细文档请查看 [README.md](README.md)
