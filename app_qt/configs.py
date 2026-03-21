"""
配置文件 - 管理所有数据路径
"""

import json
import os
from pathlib import Path
from typing import Callable

from pydantic import BaseModel

# 获取用户主目录
USER_HOME = os.path.expanduser("~")

# myhelper 数据根目录（位于用户主目录下）
MYHELPER_ROOT = os.path.join(USER_HOME, "myhelper")

# 确保根目录存在
if not os.path.exists(MYHELPER_ROOT):
    os.makedirs(MYHELPER_ROOT)

# 各模块数据路径
DATA_PATHS = {
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


def format_app_config_file_path(filename) -> Path:
    """
    获取主程序配置文件的路径，返回 Path 对象
    """
    return Path(os.path.join(MYHELPER_ROOT, "appcfg", filename))


def ensure_app_config_file(
    filename, default_value: str | Callable[[], str], interrupt_if_uninitialized=False
) -> Path:
    """
    确保此配置文件存在，如果不存在则根据default_value中的值创建
    如果 interrupt_if_uninitialized 为 True，则在配置文件未初始化时,将生成一个模板,并且中断程序
    """
    filepath = format_app_config_file_path(filename)
    if not filepath.parent.exists():
        filepath.parent.mkdir(parents=True)
    if not filepath.exists():
        filepath.write_text(
            default_value() if callable(default_value) else default_value
        )
        if interrupt_if_uninitialized:
            raise FileNotFoundError(
                f"配置文件：{filepath} 内容需要您手动编辑，这是程序正常启动前的必要配置,请打开该文件并填写相关内容.配置完成后重启程序,您将能够正常使用,谢谢!"
            )
    return filepath


class LLMConfig(BaseModel):
    """
    LLM 配置
    """

    # LLM 提供商
    provider: str
    # 当前使用的模型
    model: str
    # llm定制的名称,默认为"default",不同定制化名称下面可以用不同的提示词模板
    customization_name: str = "default"


class MainAppConfig(BaseModel):
    """
    主程序配置
    """

    llm_config: LLMConfig

    def create_default_config_json_str(self) -> str:
        return self.model_dump_json(indent=4)


# 确保主程序配置文件存在,如果不存在,需要用户手动编辑
main_config_file = ensure_app_config_file(
    "app_config.json",
    lambda: MainAppConfig(
        llm_config=LLMConfig(
            provider=input("请输入LLM提供商名称:"),
            model=input("请输入LLM模型名称, 如glm-5: "),
        )
    ).create_default_config_json_str(),
)

app_config = MainAppConfig(**json.loads(main_config_file.read_text()))
