"""
配置文件 - 管理所有数据路径
"""
import os

# 获取用户主目录
USER_HOME = os.path.expanduser("~")

# myhelper 数据根目录（位于用户主目录下）
MYHELPER_ROOT = os.path.join(USER_HOME, "myhelper")

# 确保根目录存在
if not os.path.exists(MYHELPER_ROOT):
    os.makedirs(MYHELPER_ROOT)

# 各模块数据路径
DATA_PATHS = {
    # 任务管理器数据路径
    'tasks_file': os.path.join(MYHELPER_ROOT, "daily_tasks.xlsx"),
    
    # 快速笔记数据路径
    'quick_notes_dir': os.path.join(MYHELPER_ROOT, "quick_notes"),
}

# 确保所有子目录存在
for key, path in DATA_PATHS.items():
    if not path.endswith('.xlsx'):  # Excel 文件不需要创建目录
        dir_path = os.path.dirname(path) if '.' in os.path.basename(path) else path
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)