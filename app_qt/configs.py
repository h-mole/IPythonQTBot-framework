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
    "tasks_file": os.path.join(MYHELPER_ROOT, "daily_tasks.xlsx"),
    # 快速笔记数据路径
    "quick_notes_dir": os.path.join(MYHELPER_ROOT, "quick_notes"),
    # 应用配置目录
    "appcfg_dir": os.path.join(MYHELPER_ROOT, "appcfg"),
}

# 插件相关路径
PLUGINS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "plugins"
)  # 启动路径的 plugins 文件夹
PLUGINS_CONFIG_FILE = os.path.join(
    DATA_PATHS["appcfg_dir"], "plugins_list.json"
)  # 插件启用配置

# 确保所有子目录存在
for key, path in DATA_PATHS.items():
    if not path.endswith(".xlsx"):  # Excel 文件不需要创建目录
        dir_path = os.path.dirname(path) if "." in os.path.basename(path) else path
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

# 确保插件目录存在
if not os.path.exists(PLUGINS_DIR):
    os.makedirs(PLUGINS_DIR)

# 插件数据目录
PLUGIN_DATA_DIR = os.path.join(MYHELPER_ROOT, "plugin_data")
if not os.path.exists(PLUGIN_DATA_DIR):
    os.makedirs(PLUGIN_DATA_DIR)
