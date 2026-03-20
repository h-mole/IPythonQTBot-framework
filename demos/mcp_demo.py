from mcp.server.fastmcp import FastMCP
import datetime

# 1. 初始化 MCP Server，命名为 "DailyTaskTool"
mcp = FastMCP("DailyTaskTool")

# ==========================================
# 这里是您原有的任务工具逻辑（示例）
# 在实际场景中，您可以直接 import 您现有的代码
# ==========================================
class TaskManager:
    def __init__(self):
        self.tasks = [
            {"id": 1, "content": "学习 MCP 协议", "done": False},
            {"id": 2, "content": "写日报", "done": False}
        ]

    def add_task(self, content: str) -> str:
        new_id = len(self.tasks) + 1
        self.tasks.append({"id": new_id, "content": content, "done": False})
        return f"任务 '{content}' 已添加，ID 为 {new_id}"

    def list_tasks(self) -> str:
        if not self.tasks:
            return "今日暂无任务。"
        output = "今日任务清单：\n"
        for t in self.tasks:
            status = "✅" if t["done"] else "⬜"
            output += f"{status} [{t['id']}] {t['content']}\n"
        return output

    def complete_task(self, task_id: int) -> str:
        for t in self.tasks:
            if t["id"] == task_id:
                t["done"] = True
                return f"任务 {task_id} 已完成！"
        return f"未找到 ID 为 {task_id} 的任务。"

# 实例化您的工具
manager = TaskManager()

# ==========================================
# MCP 接入层（关键步骤）
# ==========================================

# 2. 定义工具：列出任务
@mcp.tool()
def list_my_tasks() -> str:
    """
    获取当前的每日任务列表。
    当用户询问'我的任务是什么'或'今天要做什么'时调用此工具。
    """
    return manager.list_tasks()

# 3. 定义工具：添加任务
@mcp.tool()
def add_my_task(content: str) -> str:
    """
    添加一个新的每日任务。
    参数:
    - content: 任务的具体内容
    """
    return manager.add_task(content)

# 4. 定义工具：完成任务
@mcp.tool()
def finish_task(task_id: int) -> str:
    """
    将指定的任务标记为已完成。
    参数:
    - task_id: 任务的数字 ID
    """
    return manager.complete_task(task_id)

# 5. (可选) 定义资源：让 AI 能读取任务数据源
@mcp.resource("task://daily")
def get_task_data() -> str:
    """以纯文本格式暴露任务数据资源"""
    return manager.list_tasks()

if __name__ == "__main__":
    # 启动服务器
    mcp.run()
