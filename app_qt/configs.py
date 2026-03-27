"""
配置文件 - 管理所有数据路径
"""

import json
import os
from pathlib import Path
from typing import Callable

from IPython.terminal.embed import make_main_module_type
from pydantic import BaseModel
from pyside6_settings import BaseSettings, Field

# 获取用户主目录
USER_HOME = os.path.expanduser("~")

# 数据根目录（位于用户主目录下）
MYHELPER_ROOT = os.path.join(USER_HOME, "IPythonQTBot")

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


# class LLMProvider(BaseSettings):
#     """
#     LLM 提供商配置
#     """

#     name: str = Field(default="", title="Name")
#     api_key: str = Field(default="", title="API Key")
#     api_url: str = Field(default="", title="API URL")


# class LLMConfig(BaseModel):
#     """
#     LLM 配置
#     """

#     # LLM 提供商, 该字段值需要和provider_list中的<elem>.name一致
#     provider: str
#     # 当前使用的模型
#     model: str
#     # 最大上下文消息数
#     max_context_messages: int = 10
#     # llm定制的名称,默认为"default",不同定制化名称下面可以用不同的提示词模板
#     customization_name: str = "default"
#     # llm提供商列表
#     provider_list: list[LLMProvider] = []


from app_qt.i18n import _

class LLMProviderSettingsItem(BaseSettings):
    """
    LLM 提供商设置
    """

    name: str = Field(default="", title=_("Name"))
    api_key: str = Field(default="", title=_("API Key"))
    base_url: str = Field(default="", title=_("Base URL"))


class LLMConfigSettings(BaseSettings):
    """
    LLM 配置设置
    """

    provider: str = Field(default="", title=_("Provider"))
    # 当前使用的模型
    model: str = Field(default="", title=_("Model"))
    # 最大上下文消息数
    max_context_messages: int = Field(default=50, title=_("Max Context Messages"))
    # llm定制的名称,默认为"default",不同定制化名称下面可以用不同的提示词模板
    customization_name: str = Field(default="default", title=_("Customization Name"))
    # llm 提供商列表
    provider_list: list[LLMProviderSettingsItem] = Field(default=[], title=_("Provider List"))

    class Config:
        arbitrary_types_allowed = True

    def format_providers_list(self) -> str:
        s = ""
        for provider in self.provider_list:
            s += f"Provider: {provider.name}, API Key: '******', Base URL: {provider.base_url}\n"
        return s
    
    def get_current_llm_config(self) -> LLMProviderSettingsItem:
        if len(self.provider_list) == 0:
            raise ValueError("Provider list is empty")
        for provider in self.provider_list:
            if provider.name == self.provider:
                return provider
        raise ValueError(f"Provider {self.provider} not found in provider list: {self.format_providers_list()}")
class OtherSettings(BaseSettings):
    demo: str = Field(default="", title=_("Some Value"))


class LanguageSettings(BaseSettings):
    """
    语言设置
    """
    language: str = Field(
        default="auto",
        title=_("Language"),
        choices=["auto", "en", "zh_CN"],
        description=_("Select interface language. 'auto' will detect from system locale.")
    )

class MainAppConfigSettings(BaseSettings):
    # 类属性：设置表单展示模式为选项卡式
    _form_display_mode = "tabs"
    
    llm_config: LLMConfigSettings = Field(
        default_factory=LLMConfigSettings, title=_("LLM Config")
    )
    other_settings: OtherSettings = Field(
         default_factory=OtherSettings, title=_("Other Config")
    )
    language: LanguageSettings = Field(
        default_factory=LanguageSettings, title=_("Language Settings")
    )

    def is_provider_configured(self) -> bool:
        """
        检查是否已配置 LLM 提供商
        """
        return bool(self.llm_config.provider and self.llm_config.provider_list)



# 确保主程序配置文件存在，如果不存在，创建默认配置
main_config_file = ensure_app_config_file(
    "app_config.json",
    lambda: json.dumps(MainAppConfigSettings().model_dump(), indent=4),
)

# 全局 app_config 实例（用于兼容旧代码）
# app_config = MainAppConfig(**json.loads(main_config_file.read_text()))
MAIN_APP_DATA_DIR = Path(MYHELPER_ROOT) / "app_data"

# 创建全局设置实例（用于设置面板）
settings = MainAppConfigSettings.load(config_file=main_config_file, auto_create=True)
app_config = settings
