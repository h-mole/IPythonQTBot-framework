# email_utils 性能优化总结

## 主要改进

### 1. 统一 API 调用逻辑

**之前的问题：**
- `get_recent_emails_api` 函数重复实现了邮件获取逻辑
- UI 使用 `EmailFetchWorker`，API 使用独立的 IMAP 调用
- 代码维护成本高

**改进后：**
- API 直接复用 `EmailFetchWorker` 类
- 统一的邮件获取逻辑，减少代码重复
- 提供同步和异步两种调用方式

```python
def get_recent_emails_api(account_name, limit=20):
    """API: 获取最近的邮件列表 - 直接调用 UI 的获取逻辑"""
    account_config = get_account_config(account_name)
    worker = EmailFetchWorker(account_config, limit)
    
    # 通过信号槽获取结果
    result = []
    error = []
    
    def on_emails(emails):
        result.extend(emails)
    
    def on_error(err):
        error.append(err)
    
    worker.emails_fetched.connect(on_emails)
    worker.error_occurred.connect(on_error)
    worker.start()
    
    # 等待完成（最多 30 秒）
    timeout = 30
    start_time = time.time()
    while not worker.isFinished() and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if error:
        raise Exception(error[0])
    
    return result
```

### 2. 全面的异步操作

#### 新增 Worker 类

##### a. EmailDetailWorker - 获取邮件详情
```python
class EmailDetailWorker(QThread):
    """后台获取邮件详情线程"""
    
    detail_fetched = Signal(dict)  # 信号：邮件详情获取完成
    error_occurred = Signal(str)   # 信号：发生错误
    
    def __init__(self, account_name, email_id):
        super().__init__()
        self.account_name = account_name
        self.email_id = email_id
        
    def run(self):
        try:
            detail = get_email_detail_api(self.account_name, self.email_id)
            self.detail_fetched.emit(detail)
        except Exception as e:
            logger.error(f"Error fetching email detail: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
```

**使用方式：**
```python
def view_email_detail(self, row, column):
    """查看邮件详情（异步获取）"""
    email_data = self.emails_data[row]
    email_id = email_data.get('id')
    
    # 创建后台获取详情线程
    self.detail_worker = EmailDetailWorker(self.current_account, email_id)
    self.detail_worker.detail_fetched.connect(self.show_email_detail_dialog)
    self.detail_worker.error_occurred.connect(self.on_get_detail_error)
    self.detail_worker.start()

def show_email_detail_dialog(self, email_detail):
    """显示邮件详情对话框"""
    dialog = EmailDetailDialog(self, email_detail, self.current_account)
    dialog.exec()
```

##### b. DownloadAttachmentWorker - 下载附件
```python
class DownloadAttachmentWorker(QThread):
    """后台下载附件线程"""
    
    download_completed = Signal(str)  # 信号：下载完成（返回保存路径）
    error_occurred = Signal(str)      # 信号：发生错误
    
    def __init__(self, account_name, email_id, filename, save_path):
        super().__init__()
        self.account_name = account_name
        self.email_id = email_id
        self.filename = filename
        self.save_path = save_path
```

**使用方式：**
```python
def start_download(self):
    """开始下载（在后台线程中）"""
    selected_items = self.attach_list.selectedItems()
    if not selected_items:
        QMessageBox.warning(self, "警告", "请先选择要下载的附件！")
        return
    
    filename = selected_items[0].data(Qt.UserRole)
    
    # 选择保存路径（阻塞操作，但在主线程中快速完成）
    save_path, _ = QFileDialog.getSaveFileName(
        self, "保存附件", filename, "All Files (*)"
    )
    
    if save_path:
        # 创建后台下载线程
        self.download_worker = DownloadAttachmentWorker(
            self.account_name,
            self.email_detail['id'],
            filename,
            save_path
        )
        self.download_worker.download_completed.connect(self.on_download_completed)
        self.download_worker.error_occurred.connect(self.on_download_error)
        self.download_worker.start()
```

##### c. SendEmailWorker - 发送邮件
```python
class SendEmailWorker(QThread):
    """后台发送邮件线程"""
    
    send_completed = Signal(bool)  # 信号：发送完成
    error_occurred = Signal(str)   # 信号：发生错误
    
    def __init__(self, account_name, to, subject, body, attachments=None):
        super().__init__()
        self.account_name = account_name
        self.to = to
        self.subject = subject
        self.body = body
        self.attachments = attachments or []
```

**使用方式：**
```python
def start_send_email(self):
    """开始发送邮件（在后台线程中）"""
    to = self.to_edit.text().strip()
    subject = self.subject_edit.text().strip()
    body = self.body_edit.toHtml()
    
    if not to or not subject:
        QMessageBox.warning(self, "警告", "请输入收件人地址和主题！")
        return
    
    # 创建后台发送线程
    self.send_worker = SendEmailWorker(
        account_name=self.from_combo.currentText(),
        to=to,
        subject=subject,
        body=body,
        attachments=self.attachments
    )
    self.send_worker.send_completed.connect(self.on_send_completed)
    self.send_worker.error_occurred.connect(self.on_send_error)
    self.send_worker.start()
```

### 3. 信号槽机制的完善使用

#### 所有耗时操作都通过信号槽通知结果

| 操作 | Worker 类 | 成功信号 | 错误信号 |
|------|----------|---------|---------|
| 获取邮件列表 | EmailFetchWorker | emails_fetched | error_occurred |
| 获取邮件详情 | EmailDetailWorker | detail_fetched | error_occurred |
| 下载附件 | DownloadAttachmentWorker | download_completed | error_occurred |
| 发送邮件 | SendEmailWorker | send_completed | error_occurred |

#### 回调处理模式

```python
# 1. 创建 Worker
self.worker = SomeWorker(...)

# 2. 连接信号
self.worker.success_signal.connect(self.on_success)
self.worker.error_signal.connect(self.on_error)

# 3. 启动线程
self.worker.start()

# 4. 回调处理
def on_success(self, result):
    """处理成功结果"""
    # 更新 UI
    
def on_error(self, error_msg):
    """处理错误"""
    QMessageBox.critical(self, "错误", f"操作失败：{error_msg}")
```

### 4. 日志记录增强

添加了详细的日志记录：

```python
logger.info(f"Connected to IMAP server: {imap_server}:{imap_port}")
logger.info("Login to IMAP server successful")
logger.info(f"Retrieving {len(recent_ids)} emails")
logger.error(f"Error fetching emails: {e}", exc_info=True)
```

## 性能对比

### 之前的实现

| 操作 | 阻塞情况 | 用户体验 |
|------|---------|---------|
| 刷新邮件 | ✅ 阻塞 UI | ❌ 界面卡死 |
| 查看邮件详情 | ✅ 阻塞 UI | ❌ 界面卡死 |
| 下载附件 | ✅ 阻塞 UI | ❌ 界面卡死 |
| 发送邮件 | ✅ 阻塞 UI | ❌ 界面卡死 |

### 改进后的实现

| 操作 | 阻塞情况 | 用户体验 | 进度提示 |
|------|---------|---------|---------|
| 刷新邮件 | ❌ 不阻塞 | ✅ 流畅 | ✅ 进度条 |
| 查看邮件详情 | ❌ 不阻塞 | ✅ 流畅 | ⏳ 隐式等待 |
| 下载附件 | ❌ 不阻塞 | ✅ 流畅 | ✅ 对话框反馈 |
| 发送邮件 | ❌ 不阻塞 | ✅ 流畅 | ✅ 对话框反馈 |

## 代码结构优化

### 之前

```
main.py
├── EmailFetchWorker (异步获取邮件)
├── EmailManagerTab
│   ├── fetch_emails() → 创建 EmailFetchWorker
│   ├── view_email_detail() → 同步调用 API (阻塞!)
│   └── compose_email() → 同步调用 API (阻塞!)
└── API 函数
    ├── get_recent_emails_api() → 重复实现 (冗余!)
    ├── get_email_detail_api() → 同步
    └── send_email_api() → 同步
```

### 改进后

```
main.py
├── Worker 类 (全部异步)
│   ├── EmailFetchWorker
│   ├── EmailDetailWorker ✨ NEW
│   ├── DownloadAttachmentWorker ✨ NEW
│   └── SendEmailWorker ✨ NEW
├── EmailManagerTab
│   ├── fetch_emails() → EmailFetchWorker
│   ├── view_email_detail() → EmailDetailWorker ✨
│   └── compose_email() → SendEmailDialog
├── Dialog 类
│   ├── EmailDetailDialog
│   │   └── start_download() → DownloadAttachmentWorker ✨
│   └── SendEmailDialog
│       └── start_send_email() → SendEmailWorker ✨
└── API 函数
    └── get_recent_emails_api() → 复用 EmailFetchWorker ✨
```

## 关键改进点

### 1. 消除重复代码
- ✅ `get_recent_emails_api` 不再重复实现 IMAP 逻辑
- ✅ 所有耗时操作统一使用 Worker 模式

### 2. 非阻塞 UI
- ✅ 所有网络操作都在后台线程
- ✅ UI 始终保持响应
- ✅ 提供进度反馈

### 3. 错误处理
- ✅ 统一的错误信号处理
- ✅ 友好的错误提示
- ✅ 详细的日志记录

### 4. 可维护性
- ✅ 清晰的职责分离
- ✅ 一致的代码模式
- ✅ 易于扩展

## 使用示例

### 其他插件调用 API

```python
from app_qt.plugin_manager import get_plugin_manager

plugin_manager = get_plugin_manager()

# 获取最近邮件（同步调用，会阻塞）
get_emails = plugin_manager.get_method("email_utils.get_recent_emails")
try:
    emails = get_emails("我的 QQ 邮箱", limit=10)
    print(f"获取到 {len(emails)} 封邮件")
except Exception as e:
    print(f"获取失败：{e}")

# 获取邮件详情（同步调用，会阻塞）
get_detail = plugin_manager.get_method("email_utils.get_email_detail")
detail = get_detail("我的 QQ 邮箱", email_id)
print(f"邮件主题：{detail['subject']}")
```

### UI 中使用（异步，推荐）

```python
# 刷新邮件（异步，不阻塞）
self.fetch_worker = EmailFetchWorker(account_config, limit=20)
self.fetch_worker.emails_fetched.connect(self.on_emails_fetched)
self.fetch_worker.error_occurred.connect(self.on_fetch_error)
self.fetch_worker.start()

# 查看邮件详情（异步，不阻塞）
self.detail_worker = EmailDetailWorker(account_name, email_id)
self.detail_worker.detail_fetched.connect(self.show_dialog)
self.detail_worker.error_occurred.connect(self.on_error)
self.detail_worker.start()
```

## 注意事项

### 1. Worker 生命周期管理
- 需要保持对 Worker 的引用（如 `self.worker`），否则会被垃圾回收
- 多个 Worker 实例可以并存，互不影响

### 2. 同步 API 的使用限制
- `get_recent_emails_api` 等 API 提供了同步版本供其他插件调用
- **不要在 GUI 主线程中调用同步 API**，会导致界面卡死
- 建议在后台线程或其他插件的 Worker 中调用

### 3. 文件对话框
- 文件选择对话框（`QFileDialog`）仍在主线程中
- 这是合理的，因为用户交互需要阻塞等待
- 真正的耗时操作（下载、发送）已移到后台线程

## 总结

通过这次重构，我们实现了：

1. ✅ **统一的异步架构** - 所有耗时操作都使用后台线程
2. ✅ **消除重复代码** - API 复用 UI 的 Worker 逻辑
3. ✅ **完善的信号槽机制** - 所有异步操作都通过信号通信
4. ✅ **优秀的用户体验** - UI 始终流畅，有进度反馈
5. ✅ **易于维护扩展** - 清晰的代码结构，一致的模式

这些改进使得 `email_utils` 插件在性能和代码质量上都有了显著提升！
