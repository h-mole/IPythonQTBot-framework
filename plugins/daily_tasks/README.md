# 每日任务提醒器插件

## 功能介绍

每日任务提醒器插件提供了完整的任务管理功能，包括：

- ✅ 添加、编辑、删除任务
- ✅ 任务分类管理（大类/小类）
- ✅ 任务状态跟踪（未完成/已完成/进行中/已取消）
- ✅ 智能提醒系统（每天/当天/仅一次）
- ✅ 多选筛选器（按类别、状态等）
- ✅ 按日期范围过滤任务
- ✅ 系统通知提醒

## 数据格式

### 任务数据结构

Excel 文件 `daily_tasks.xlsx` 包含以下列：

| 列名 | 说明 | 示例 |
|------|------|------|
| ID | 任务 ID（自动生成） | 1 |
| 任务大类 | 任务所属分类 | 论文、项目 |
| 任务小类 | 任务子分类 | 行政、开发 |
| 任务说明 | 详细描述任务内容 | 完成论文初稿 |
| 任务完成日期 | 截止日期（格式：yyyy-MM-dd） | 2026-03-25 |
| 提醒方式 | 提醒频率（每天/当天/仅一次） | 当天 |
| 提醒时间 | 具体提醒时间（格式：HH:mm） | 09:00 |
| 完成状态 | 任务状态 | 未完成/已完成/进行中/已取消 |
| 备注 | 补充说明 | 需要包含实验数据 |

### 数据存储位置

- 任务数据：`plugins/daily_tasks/data/daily_tasks.xlsx`
- 分类配置：`plugins/daily_tasks/data/categories.json`

## API 接口

其他插件可以通过以下方式调用任务管理功能：

```python
# 获取插件管理器
from app_qt.plugin_manager import get_plugin_manager
plugin_manager = get_plugin_manager()

# 获取任务管理 API
add_task = plugin_manager.get_method("daily_tasks.add_task")
delete_task = plugin_manager.get_method("daily_tasks.delete_task")
get_tasks = plugin_manager.get_method("daily_tasks.get_tasks")
get_task_by_id = plugin_manager.get_method("daily_tasks.get_task_by_id")
update_task = plugin_manager.get_method("daily_tasks.update_task")
filter_by_date = plugin_manager.get_method("daily_tasks.filter_tasks_by_date")
mark_complete = plugin_manager.get_method("daily_tasks.mark_task_complete")

# 示例：添加任务
task_id = add_task({
    "category": "项目",
    "subcategory": "开发",
    "description": "完成插件系统开发",
    "due_date": "2026-03-30",
    "reminder_type": "当天",
    "reminder_time": "09:00",
    "status": "未完成",
    "notes": "优先级高"
})

# 示例：获取所有未完成任务
tasks = get_tasks({"status": "未完成"})

# 示例：按日期范围过滤
today_tasks = filter_by_date("2026-03-19", "2026-03-19")

# 示例：更新任务
update_task(task_id, {"status": "进行中"})

# 示例：标记任务完成
mark_complete(task_id)

# 示例：删除任务
delete_task(task_id)
```

## 使用方法

### 1. 添加任务

1. 点击 **"➕ 添加任务"** 按钮
2. 填写任务信息：
   - 任务大类/小类：可输入已有分类或创建新分类
   - 任务说明：详细描述任务内容
   - 完成日期：选择任务截止日期
   - 提醒方式：选择提醒频率
   - 提醒时间：设置具体提醒时间
   - 完成状态：初始状态
   - 备注：补充说明
3. 点击 **"确定"** 保存

### 2. 编辑任务

- **方法一**：选中任务后点击 **"✏️ 编辑任务"**
- **方法二**：双击任务所在行

### 3. 删除任务

1. 选中要删除的任务
2. 点击 **"🗑️ 删除任务"**
3. 确认删除

### 4. 标记任务完成

1. 选中任务
2. 点击 **"✅ 标记完成"**

### 5. 筛选任务

使用顶部的多选筛选器：
- 任务大类：可选择多个大类
- 任务小类：可选择多个小类
- 完成状态：可选择多个状态

点击筛选按钮，在弹出菜单中选择或取消选择各项。

### 6. 排序任务

- **按类别**：先按大类排序，再按小类排序
- **按截止期限**：按任务完成日期排序
- **倒序**：反转排序顺序

## 提醒规则

### 提醒方式

1. **每天**：每天都在指定时间提醒
2. **当天**：只在完成日期当天提醒
3. **仅一次**：只提醒一次

### 特殊日期类型

- **一般日期**：普通截止日期
- **无固定期限**：没有明确截止日期的任务
- **长期**：长期进行的任务

## 分类管理

插件会自动记录新增的分类，并保存在 `categories.json` 中。

### 自定义分类

编辑 `plugins/daily_tasks/data/categories.json`：

```json
{
  "categories": ["论文", "项目", "工作", "学习"],
  "subcategories": ["行政", "项目", "会议", "学习", "研究"]
}
```

## 注意事项

1. 任务数据自动保存，无需手动保存
2. 系统会在指定时间通过 plyer 发送桌面通知
3. 如果系统通知失败，会回退到弹窗提醒
4. 重启应用后会重置已通知记录，避免漏提醒
5. 支持从 Excel 格式迁移过来的旧数据

## 依赖

- PySide6：GUI 框架
- plyer：系统通知功能
