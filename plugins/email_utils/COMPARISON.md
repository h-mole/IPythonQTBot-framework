# email_utils vs daily_tasks 对比

## 架构对比

### 相似之处

| 特性 | daily_tasks | email_utils |
|------|-------------|-------------|
| 插件结构 | ✅ 相同 | ✅ 相同 |
| plugin.json 配置 | ✅ 相同 | ✅ 相同 |
| API 导出机制 | ✅ 相同 | ✅ 相同 |
| 数据目录结构 | ✅ data/ | ✅ data/ |
| 初始化脚本 | ✅ init_data.py | ✅ init_data.py |
| README 文档 | ✅ README.md | ✅ README.md |
| 测试脚本 | ❌ 无 | ✅ test_email_utils.py |
| 快速开始指南 | ❌ 无 | ✅ QUICKSTART.md |

### 数据文件对比

| 组件 | 数据文件类型 | 文件位置 | 用途 |
|------|-------------|----------|------|
| daily_tasks | Excel (.xlsx) + JSON | `data/daily_tasks.xlsx`<br>`data/categories.json` | 存储任务数据<br>存储分类配置 |
| email_utils | JSON | `data/email_accounts.json` | 存储邮箱账号配置 |

**说明：**
- daily_tasks 使用 Excel 因为需要结构化存储大量任务数据，支持复杂查询
- email_utils 只存储配置信息，邮件数据实时从服务器获取

## UI 组件对比

### daily_tasks 主要组件

1. **MultiSelectFilter** - 多选筛选器
2. **TaskDialog** - 任务编辑对话框
3. **TasksManagerTab** - 主界面标签页

### email_utils 主要组件

1. **EmailFetchWorker** - 后台邮件获取线程
2. **EmailDetailDialog** - 邮件详情对话框
3. **SendEmailDialog** - 发送邮件对话框
4. **EmailManagerTab** - 主界面标签页
5. **AccountConfigDialog** - 账号配置对话框
6. **EmailAccountDialog** - 单个账号编辑对话框

## 功能特性对比

### daily_tasks 核心功能

- ✅ 任务 CRUD（增删改查）
- ✅ 多选筛选（类别、状态）
- ✅ 排序（按类别、按日期）
- ✅ 系统通知提醒
- ✅ 特殊日期处理（长期、无期限）
- ✅ 分类管理
- ✅ API 导出（8 个方法）

### email_utils 核心功能

- ✅ 多账号管理
- ✅ 邮件收取（后台线程）
- ✅ 邮件预览（富文本 HTML）
- ✅ 附件下载
- ✅ 邮件发送（HTML+ 附件）
- ✅ 账号配置界面
- ✅ API 导出（6 个方法）

## API 对比

### daily_tasks API

```python
add_task              # 添加任务
delete_task           # 删除任务
get_tasks             # 获取任务列表
get_todo_tasks        # 获取未完成任务
get_task_by_id        # 根据 ID 获取任务
update_task           # 更新任务
filter_tasks_by_date  # 按日期过滤
mark_task_complete    # 标记完成
```

### email_utils API

```python
get_recent_emails     # 获取最近邮件
get_email_detail      # 获取邮件详情
send_email            # 发送邮件
get_attachments       # 获取附件列表
download_attachment   # 下载附件
get_accounts          # 获取所有账号
```

## 技术实现差异

### 数据获取方式

**daily_tasks:**
- 本地 Excel 文件读写
- 同步操作
- openpyxl 库

**email_utils:**
- 远程 IMAP/SMTP服务器
- 异步操作（QThread 后台线程）
- Python 标准库（imaplib, smtplib, email）

### 数据处理

**daily_tasks:**
- 直接操作 Excel 数据
- 内存中维护任务列表
- 定时保存

**email_utils:**
- 实时从服务器获取
- 解析 MIME 格式邮件
- HTML 渲染（QTextBrowser）
- 附件二进制处理

### 用户交互

**daily_tasks:**
- 表格展示
- 双击编辑
- 多选筛选
- 系统通知（plyer）

**email_utils:**
- 表格展示
- 双击查看详情
- 富文本预览
- 附件下载对话框

## 配置文件对比

### daily_tasks 配置

```json
{
  "categories": ["论文", "项目"],
  "subcategories": ["行政", "项目", "会议", "学习"]
}
```

### email_utils 配置

```json
{
  "accounts": [
    {
      "name": "账号名称",
      "username": "邮箱地址",
      "password": "密码/授权码",
      "imap_server": "IMAP 服务器",
      "smtp_server": "SMTP 服务器",
      ...
    }
  ]
}
```

## 依赖对比

### daily_tasks 依赖

```
PySide6          # GUI
openpyxl         # Excel 处理
plyer            # 系统通知
```

### email_utils 依赖

```
PySide6          # GUI
beautifulsoup4   # HTML 解析
imaplib2         # IMAP 接收（可选，可用标准库）
# 其他都是 Python 标准库
```

## 安全考虑

### daily_tasks

- 本地数据存储
- 无需网络
- 数据隐私依赖本地安全

### email_utils

- 敏感信息（密码）本地存储
- 需要网络连接
- SSL/TLS加密传输
- 建议使用授权码而非真实密码
- 配置文件需要保护

## 使用场景

### daily_tasks

适合：
- 个人任务管理
- 项目进度跟踪
- 待办事项提醒
- 截止日期管理

### email_utils

适合：
- 多账号邮件统一管理
- 快速查看最新邮件
- 批量下载附件
- 集成到工作流中的邮件处理

## 扩展性

### daily_tasks 可扩展点

- 任务优先级
- 任务依赖关系
- 甘特图展示
- 团队协作
- 日历视图

### email_utils 可扩展点

- 邮件搜索
- 邮件过滤规则
- 自动分类
- 邮件模板
- 定时发送
- 邮件归档
- 多个文件夹管理

## 总结

两个插件都遵循相同的插件架构规范，但针对不同的使用场景进行了优化：

- **daily_tasks** 更注重数据的结构化存储和本地管理
- **email_utils** 更注重网络通信和实时数据获取

两者都提供了完整的 UI 界面和 API 接口，可以独立使用或被其他插件调用。
