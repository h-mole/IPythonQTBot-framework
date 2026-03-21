"""
IPython LLM Bridge - 流式对话框架
功能：
1. 在 IPython 中提供 agent 变量来访问 LLM 对话功能
2. 支持 agent.ask("问题") 进行流式对话
3. 支持 agent.clear() 清除历史对话
4. 支持 %agent_ask 和 %agent_clear magic 命令
5. 自动集成 MCP 工具（从 plugin_manager 中 enable_mcp=True 的方法）
6. 支持多 LLM 提供商配置
"""

import os
import queue
import sys
import textwrap
import threading
from typing import Literal, Optional, List, Dict, Any, TYPE_CHECKING
from IPython.core.getipython import get_ipython
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QApplication
import json
import sys
import yaml
from rich import print
from rich.text import Text
from app_qt.plugin_manager import PluginManager, get_plugin_manager
from qtpy.QtCore import QThread
from IPython.display import Markdown, display
from app_qt.configs import (
    format_app_config_file_path,
    ensure_app_config_file,
    app_config,
)
if TYPE_CHECKING:
    from .ipython_console_tab import IPythonConsoleTab

# 导入 OpenAI SDK
try:
    from openai import OpenAI
except ImportError:
    print("[警告] 未安装 openai 库，请运行：pip install openai")
    OpenAI = None
from dotenv import load_dotenv

load_dotenv()
import logging

logger = logging.getLogger(__name__)


class LLMConfig:
    """LLM 配置类"""

    # 预定义的 LLM 提供商配置
    PROVIDERS = {
        "kimi": {
            "base_url": "https://api.moonshot.cn/v1",
            "model": "kimi-k2.5",
            "env_key": "KIMI_API_KEY",
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-3.5-turbo",
            "env_key": "OPENAI_API_KEY",
        },
        "zhipu": {
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "model": "glm-4",
            "env_key": "ZHIPU_API_KEY",
        },
        "aliyun": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "glm-5",
            "env_key": "ALIYUN_API_KEY",
        },
    }

    def __init__(
        self,
        provider: str = "kimi",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        初始化 LLM 配置

        Args:
            provider: 提供商名称 ("kimi", "openai", "zhipu")
            api_key: API Key（如果不提供则从环境变量读取）
            base_url: API 基础 URL（可选，会覆盖默认值）
            model: 模型名称（可选，会覆盖默认值）
        """
        if provider not in self.PROVIDERS:
            raise ValueError(
                f"不支持的 LLM 提供商：{provider}，支持的有：{list(self.PROVIDERS.keys())}"
            )

        self.provider = provider
        provider_config = self.PROVIDERS[provider]

        # 获取 API Key
        self.api_key = api_key or os.getenv(provider_config["env_key"])
        if not self.api_key:
            raise ValueError(
                f"未提供 API Key，请设置 api_key 参数或环境变量 {provider_config['env_key']}"
            )

        # 获取 Base URL
        self.base_url = base_url or provider_config["base_url"]

        # 获取 Model
        self.model = model or provider_config["model"]

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "provider": self.provider,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model": self.model,
        }


class StreamingOutputHandler(QObject):
    """流式输出处理器 - 在后台线程中执行 LLM 请求"""

    chunk_text_updated = Signal(str)  # 发射输出的文本块
    llm_message_finish = Signal(dict)  # 发射完整响应
    stream_finish = Signal(
        str
    )  # 表征stream已经结束，str的意思是下一步怎么办，如 "CALL_TOOL" 指的是需要调用工具，而"FINISH"代表直接结束即可。
    error_occurred = Signal(str)  # 发射错误信息

    IMPORTANT_STYLE = "bold"
    DIM_STYLE = "#999999"

    def __init__(self, ipython_shell=None, agent_instance: "Agent"=None):
        super().__init__()
        self.is_streaming = False
        self.ipython_shell = ipython_shell  # IPython shell 引用
        self.response_queue = queue.Queue()
        self.current_stdout = sys.stdout
        self.agent_instance = agent_instance  # Agent 实例引用
        self.start_timer()
        

    def start_timer(self):
        def timer_func():
            try:
                while True:
                    chunk = self.response_queue.get_nowait()
                    print(chunk, end="", file=self.current_stdout, flush=True)
            except queue.Empty:
                # 刷新UI线程，避免卡顿
                QTimer.singleShot(20, timer_func)

        self._timer = QTimer.singleShot(0, timer_func)

    def set_current_stdout_stream(self, stdout):
        self.current_stdout = sys.stdout

    def stream_response(
        self, client, messages: List[Dict], tools: Optional[List[Dict]] = None
    ):
        """
        在独立线程中执行流式请求

        Args:
            client: OpenAI 客户端
            messages: 对话历史
            tools: 工具列表（可选）
        """

        thread = threading.Thread(
            target=self._stream_thread, args=(client, messages, tools), daemon=True
        )
        thread.start()

    def _stream_thread(self, client, messages: List[Dict], tools: Optional[List[Dict]]):
        """流式请求的线程函数 (重写版)"""
        try:
            self.is_streaming = True

            # 构建请求参数
            request_params = {
                "model": os.getenv("MODEL"),
                "messages": messages,
                "stream": True,
            }

            # 如果提供了工具，添加到请求
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = "auto"
            print((f"请求发起，等待处理..."))
            # 发起流式请求
            response = client.chat.completions.create(**request_params)

            full_response = ""
            reasoning_content = ""  # 思维链
            # reasoning_enabled = False
            # 使用字典按 index 存储工具调用碎片，解决流式拼接问题
            tool_calls_map = {}

            # 记忆当前正在输出的内容
            current_output: Literal["content", "reasoning_content", "tool_call"] = ""

            # ===========================
            # 第一阶段：接收并拼接流式数据
            # ===========================
            for chunk in response:
                if not self.is_streaming:
                    self.response_queue.put(Text("Streaming has been canceled by user.", style="cyan"))
                    break

                # 安全检查
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                # 1. 处理文本内容
                if delta.content:
                    if current_output != "content":
                        current_output = "content"
                        self.response_queue.put(
                            Text("\n\n输出结果:\n\n", style=self.IMPORTANT_STYLE)
                        )
                    full_response += delta.content
                    self.response_queue.put(delta.content)
                #   处理reasoning_content
                if (
                    hasattr(delta, "reasoning_content")
                    and delta.reasoning_content is not None
                ):
                    if current_output != "reasoning_content":
                        current_output = "reasoning_content"
                        self.response_queue.put(
                            Text("\n\n思维过程:\n\n", style=self.IMPORTANT_STYLE)
                        )
                    self.response_queue.put(
                        Text(delta.reasoning_content, style=self.DIM_STYLE)
                    )
                    # reasoning_enabled = True
                    reasoning_content += delta.reasoning_content
                # 2. 处理工具调用碎片
                if hasattr(delta, "tool_calls") and delta.tool_calls:
                    if current_output != "tool_call":
                        current_output = "tool_call"
                        self.response_queue.put(
                            Text("\n\n工具调用过程:\n\n", style=self.IMPORTANT_STYLE)
                        )
                    for tool_call_chunk in delta.tool_calls:
                        # 获取索引，OpenAI 流式返回通过 index 标识不同的工具调用
                        idx = getattr(tool_call_chunk, "index", 0)

                        # 初始化该索引的字典结构
                        if idx not in tool_calls_map:
                            tool_calls_map[idx] = {
                                "id": None,
                                "type": "function",
                                "function": {"name": None, "arguments": ""},
                            }

                        current_tc = tool_calls_map[idx]

                        # 拼接 ID (通常在第一个 chunk)
                        if hasattr(tool_call_chunk, "id") and tool_call_chunk.id:
                            current_tc["id"] = tool_call_chunk.id
                            self.response_queue.put(
                                Text(
                                    f"\nTool Call ID: {tool_call_chunk.id}",
                                    style=self.DIM_STYLE,
                                )
                            )

                        # 拼接 Function 信息
                        if (
                            hasattr(tool_call_chunk, "function")
                            and tool_call_chunk.function
                        ):
                            func_chunk = tool_call_chunk.function

                            if hasattr(func_chunk, "name") and func_chunk.name:
                                current_tc["function"]["name"] = func_chunk.name
                                self.response_queue.put(
                                    Text(
                                        f"Tool Call Function Name: {func_chunk.name}\n",
                                        style=self.DIM_STYLE,
                                    )
                                )

                            if (
                                hasattr(func_chunk, "arguments")
                                and func_chunk.arguments
                            ):
                                # arguments 是字符串，需要累加
                                current_tc["function"][
                                    "arguments"
                                ] += func_chunk.arguments
                                self.response_queue.put(
                                    Text(
                                        f"Tool Call Function Arguments: {func_chunk.arguments}\n",
                                        style=self.DIM_STYLE,
                                    )
                                )
            # ===========================
            # 第二阶段：构建 Assistant 消息并保存
            # ===========================
            # 将 map 转为 list
            final_tool_calls = [
                tool_calls_map[i] for i in sorted(tool_calls_map.keys())
            ]

            assistant_message = {
                "role": "assistant",
                "content": full_response if full_response else None,
                # 必须转为 None，或者不包含该字段，避免发送空字符串
            }
            if reasoning_content:
                assistant_message["reasoning_content"] = reasoning_content
            # 只有确实有工具调用时才添加 tool_calls 字段
            if final_tool_calls:
                assistant_message["tool_calls"] = final_tool_calls
                # 加上这句试试看有没有问题
                # if "reasoning_content" not in assistant_message and reasoning_enabled:
                assistant_message["reasoning_content"] = (
                    reasoning_content if reasoning_content else None
                )
            elif reasoning_content:
                assistant_message["reasoning_content"] = reasoning_content
            # ===========================
            # 第三阶段：执行工具并追加结果
            # ===========================
            tool_results_messages_storage = []
            if final_tool_calls:
                self.response_queue.put(
                    Text("\n\n[系统] 检测到工具调用，正在处理...", style="bold")
                )

                for tool_call in final_tool_calls:
                    tool_call_id = tool_call["id"]
                    function_name = tool_call["function"]["name"]
                    arguments_str = tool_call["function"]["arguments"]

                    if not function_name:
                        continue

                    self.response_queue.put(
                        Text(f"\n[系统] 调用工具：{function_name}", style="bold")
                    )

                    # 解析参数
                    try:
                        arguments = json.loads(arguments_str) if arguments_str else {}
                    except json.JSONDecodeError as e:
                        self.response_queue.put(
                            Text(f"\n[警告] 参数解析失败：{e}", style="red")
                        )
                        arguments = {}

                    # 执行工具
                    try:
                        if self.agent_instance:
                            result = self.agent_instance._execute_tool(
                                function_name, arguments
                            )

                            # 结果转字符串
                            result_str = (
                                str(result) if not isinstance(result, str) else result
                            )

                            self.response_queue.put(
                                Text(
                                    f"\n[系统] 工具 {function_name} 返回：{result_str[:100]}...\n",
                                    style=self.DIM_STYLE,
                                )
                            )

                            # 构建 tool 结果消息
                            tool_result_message = {
                                "role": "tool",
                                "tool_call_id": tool_call_id,  # 这里的 ID 来源于拼接好的数据
                                "name": function_name,  # 建议加上 name 字段
                                "content": result_str,
                            }

                            tool_results_messages_storage.append(tool_result_message)
                            # 2. 发送信号 (供 UI 显示)
                            # self.llm_message_finish.emit(tool_result_message)
                        else:
                            err_msg = Text("\n[错误] Agent 实例未初始化", style="red")
                            self.response_queue.put(err_msg)

                    except Exception as e:
                        import traceback

                        traceback.print_exc()
                        error_msg = f"\n[错误] 执行工具失败：{e}"
                        self.response_queue.put(Text(error_msg, style="red"))
                        # 将错误信息反馈给模型
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": f"Tool execution error: {str(e)}",
                            }
                        )

            # 完成响应信号，并且将工具结果发送到上级组件。
            # 【关键修复】必须先将 assistant 消息加入历史，然后再执行工具
            # 这样后续添加 tool 消息时，模型才能找到对应的请求源头
            self.llm_message_finish.emit(assistant_message)
            for tool_message in tool_results_messages_storage:
                self.llm_message_finish.emit(tool_message)
            self.is_streaming = False
            if len(tool_results_messages_storage) > 0:
                self.stream_finish.emit("CALL_TOOL")
            else:
                self.stream_finish.emit("FINISH")

        except Exception as e:
            self.is_streaming = False
            error_msg = f"\n[错误] {type(e).__name__}: {str(e)}"
            self.response_queue.put(Text(error_msg, style="red"))
            self.agent_instance.ipython_tab.ipython_status_change.emit("idle")
            self.error_occurred.emit(error_msg)
            print(f"[LLM Bridge] 流式请求错误：{e}", file=sys.stderr)
            import traceback

            traceback.print_exc()

    def stop(self):
        """停止流式输出"""
        self.is_streaming = False
        if self.response_queue is not None:
            self.response_queue.put(None)


AGENT_SYSTEM_PROMPT_INITIAL = """

You are a helpful assistant that have various functions.

## Knowledge Source
- Online: You may search online if needed.
- Local: 
    - For something that is not tasks, you may query from the local notes or textfiles;
    - For tasks involving coding, file operations, or multi-step processes: You MUST FIRST check task_requirements/
      For other simple tasks, you may proceed but should mention if task_requirements/ check is needed

## Notice

- For all tasks that you think is complex, please refer to the notes in `task_requirements/` first, or you may waste a lot of time to solve that.

"""


class Agent:
    """LLM Agent - 管理对话历史和调用"""
    
    def __init__(
        self,
        ipython_tab: "IPythonConsoleTab" ,
        config: Optional[LLMConfig] = None,
        plugin_manager=None,
        ipython_shell=None,
    ):
        """
        初始化 Agent

        Args:
            config: LLM 配置（可选，默认使用 Kimi）
            plugin_manager: 插件管理器实例（用于获取 MCP 工具）
            ipython_shell: IPython shell 实例（用于正确输出到 IPython 控制台）
        """
        self.ipython_tab = ipython_tab
        
        self.system_prompt_file = ensure_app_config_file(
            f"prompt-templates/{app_config.llm_config.customization_name}/System.md",
            AGENT_SYSTEM_PROMPT_INITIAL,
        )
        if OpenAI is None:
            raise ImportError("请先安装 openai 库：pip install openai")

        # 使用默认配置（Kimi）
        self.config = config or LLMConfig(provider="aliyun")
        print("Config", self.config, self.config.provider)
        # 创建 OpenAI 客户端
        self.client = OpenAI(api_key=self.config.api_key, base_url=self.config.base_url)

        # 对话历史
        self.messages: List[Dict[str, str]] = [{
            "role": "system",
            "content": self.system_prompt_file.read_text(),
        }]

        # 插件管理器
        self.plugin_manager: "PluginManager" = plugin_manager

        # 流式输出处理器
        self.output_handler = StreamingOutputHandler(
            ipython_shell=ipython_shell, agent_instance=self
        )

        # 保存 IPython shell 引用
        self.ipython_shell = ipython_shell

        # 绑定信号到输出方法
        self.output_handler.chunk_text_updated.connect(self._on_response_update)
        self.output_handler.llm_message_finish.connect(self._on_message_recv)
        self.output_handler.error_occurred.connect(self._on_error)
        self.output_handler.stream_finish.connect(self._on_stream_finish)

        # 当前是否在处理工具调用
        self._processing_tool_calls = False
        
        # MCP 工具过滤条件
        self.mcp_tools_enabled = set()  # 启用的工具集合，如果为空则表示全部启用
        self.mcp_tools_disabled = set()  # 禁用的工具集合

        print(
            f"[Agent] 已初始化，使用提供商：{self.config.provider}, 模型：{self.config.model}"
        )
        if self.plugin_manager:
            mcp_tools = self._build_mcp_tools()
            print(f"[Agent] 已加载 {len(mcp_tools)} 个 MCP 工具")

    def ask(self, prompt: str = ""):
        """
        向 LLM 提问（流式输出）

        Args:
            prompt: 用户问题
        """
        if prompt != "":
            # 添加用户消息到历史
            self.messages.append({"role": "user", "content": prompt})
        
        # 通知开始生成
        self.ipython_tab.ipython_status_change.emit("generating")
        
        # 构建 MCP 工具列表
        tools = self._build_mcp_tools()
        # 开始流式请求
        print(f"\n[Agent] 提问：{prompt}\n")
        print("-" * 60)
        
        
        
        self.output_handler.set_current_stdout_stream(sys.stdout)
        self.output_handler.stream_response(
            self.client, self.messages.copy(), tools if tools else None
        )

    def show_tools(self, detailed=False):
        """列出可用工具"""
        tools = self._build_mcp_tools()
        if detailed:
            print(f"[Agent] 可用工具：\n{yaml.dump(tools, allow_unicode=True)}")
        else:
            tools_brief_info = []
            for i, tool in enumerate(tools):
                tools_brief_info.append(
                    f"{i+1}. {tool["function"]['name']}:\n{tool["function"]['description']}"
                )
            print(f"[Agent] 可用工具：\n{'\n'.join(tools_brief_info)}")

    def clear(self):
        """清除历史对话"""
        self.messages.clear()
        self.messages.append({
            "role": "system",
            "content": self.system_prompt_file.read_text(),
        })
        print("[Agent] 已清除历史对话，可以开始新对话")

    def set_system_prompt(self, system_prompt: str):
        """
        设置系统提示词

        Args:
            system_prompt: 系统提示词
        """
        # 如果已有系统提示，替换它
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = system_prompt
        else:
            # 否则在开头添加
            self.messages.insert(0, {"role": "system", "content": system_prompt})
        print(f"[Agent] 已设置系统提示词：{system_prompt[:50]}...")

    def update_mcp_tools_filter(self, enabled_tools: list, disabled_tools: list):
        """
        更新 MCP 工具的过滤条件
            
        Args:
            enabled_tools: 启用的工具名称列表
            disabled_tools: 禁用的工具名称列表
        """
        self.mcp_tools_enabled = set(enabled_tools)
        self.mcp_tools_disabled = set(disabled_tools)
        print(f"[Agent] MCP 工具过滤已更新：启用 {len(self.mcp_tools_enabled)} 个，禁用 {len(self.mcp_tools_disabled)} 个")
            
        # 重新构建工具列表
        mcp_tools = self._build_mcp_tools()
        print(f"[Agent] 当前可用 MCP 工具数量：{len(mcp_tools)}")
    
    def _build_mcp_tools(self) -> List[Dict]:
        """
        从插件管理器构建 MCP 工具列表
    
        Returns:
            OpenAI Tools 格式的工具列表
        """
        if not self.plugin_manager:
            return []
    
        tools = []
    
        # 遍历所有注册的方法
        all_methods = self.plugin_manager.get_all_methods(include_extra_data=True)
    
        for method_info in all_methods:
            extra_data = method_info.get('extra_data', {})
    
            # 只选择启用了 MCP 的方法
            if not extra_data.get('enable_mcp', False):
                continue
                
            # 检查是否在禁用列表中
            method_name = method_info['name']
            if method_name in self.mcp_tools_disabled:
                continue
                
            # 如果启用了过滤（enabled_tools 不为空），则只包含在启用列表中的工具
            if self.mcp_tools_enabled and method_name not in self.mcp_tools_enabled:
                continue
    
            # 获取方法对象
            method_func = self.plugin_manager.get_method(method_name)
            if not method_func:
                continue
    
            # 获取详细信息，如果信息中已经包含了 LLM Tool 的信息，那么就直接读取
            method_metadata = self.plugin_manager.get_method_metadata(method_name)
            if method_metadata and 'llm_tool_info' in method_metadata:
                tools.append(method_metadata['llm_tool_info'])
            else:
                # 构建工具定义
                tool_def = self._method_to_openai_tool(method_name, method_func)
                if tool_def:
                    tools.append(tool_def)
    
        return tools

    def _on_stream_finish(self, next_action: Literal["FINISH", "CALL_TOOL"]):
        """
        处理流式输出完成事件
        """
        if next_action == "CALL_TOOL":
            # 需要调用工具，继续发送请求
            tools = self._build_mcp_tools()

            self.output_handler.stream_response(
                self.client, self.messages.copy(), tools if tools else None
            )
            self.ipython_tab.ipython_status_change.emit("generating")
        else:
            # 没有 CALL_TOOL，说明生成完全结束，通知 UI 更新为完成状态
            self.ipython_tab.ipython_status_change.emit("finished")
            return

    def _method_to_openai_tool(self, method_name: str, method_func) -> Optional[Dict]:
        """
        使用 MCP 包的类型解析机制将插件方法转换为 OpenAI Tool 格式

        Args:
            method_name: 方法全名 (如 "text_helper.get_text")
            method_func: 方法对象

        Returns:
            OpenAI Tool 格式的字典
        """
        import inspect

        try:

            # 从装饰后的函数中提取工具信息
            # MCP 会将类型注解转换为 JSON Schema
            sig = inspect.signature(method_func)

            # 构建参数 schema（使用 MCP 的类型映射）
            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                # 跳过 self 和 cls 参数
                if param_name in ("self", "cls"):
                    continue

                # 使用 MCP 的类型推断机制
                param_type = self._infer_param_type(param.annotation)

                # 从文档字符串提取参数描述
                param_desc = self._extract_param_description(
                    method_func, param_name, sig
                )

                properties[param_name] = {"type": param_type, "description": param_desc}

                # 如果没有默认值，则是必填参数
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            # 从文档字符串提取函数描述
            func_desc = self._extract_function_description(method_func)

            # 构建工具定义
            tool = {
                "type": "function",
                "function": {
                    "name": f"call_{method_name.replace('.', '__')}",
                    "description": func_desc,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            }

            return tool
        except Exception as e:
            print(f"[LLM Bridge] 转换方法为工具失败：{method_name}, 错误：{e}")
            return None

    def _infer_param_type(self, annotation) -> str:
        """
        使用 MCP 的类型映射机制推断参数类型

        Args:
            annotation: 类型注解

        Returns:
            str: OpenAI 支持的类型名称
        """
        import inspect as inspect_module
        import typing

        if annotation == inspect_module.Parameter.empty:
            return "string"

        # MCP 使用的类型映射（基于 Pydantic）
        type_mapping = {
            int: "integer",
            float: "number",
            bool: "boolean",
            str: "string",
            list: "array",
            dict: "object",
            List: "array",
            Dict: "object",
        }

        # 直接映射
        if annotation in type_mapping:
            return type_mapping[annotation]

        # 处理 typing 泛型
        origin = typing.get_origin(annotation)
        if origin:
            if origin in (list, List):
                return "array"
            elif origin in (dict, Dict):
                return "object"

        return "string"

    def _extract_param_description(self, method_func, param_name: str, sig) -> str:
        """
        从文档字符串中提取参数描述

        Args:
            method_func: 方法对象
            param_name: 参数名称
            sig: 方法签名

        Returns:
            str: 参数描述
        """
        import inspect as insp_module

        doc = insp_module.getdoc(method_func)
        if not doc:
            return f"Parameter {param_name}"

        # 尝试从 Google/NumPy 风格文档字符串提取
        lines = doc.split("\n")
        in_args_section = False
        current_param_lines = []

        for line in lines:
            line_stripped = line.strip()

            # 检测 Args/Parameters 部分
            if line_stripped.lower() in (
                "args:",
                "arguments:",
                "parameters:",
                "param:",
            ):
                in_args_section = True
                continue

            if in_args_section:
                # 检测新的部分开始
                if line_stripped and not line.startswith(" ") and ":" in line_stripped:
                    break

                # 匹配参数行：param_name: description 或 param_name (type): description
                if line_stripped.startswith(
                    f"{param_name}:"
                ) or line_stripped.startswith(f"{param_name} ("):
                    # 提取描述部分
                    desc_start = line_stripped.find(":") + 1
                    if desc_start > 0:
                        return line_stripped[desc_start:].strip()

                # 多行描述
                if current_param_lines and line.startswith("   "):
                    current_param_lines.append(line_stripped)

        return f"Parameter {param_name}"

    def _extract_function_description(self, method_func) -> str:
        """
        从文档字符串中提取函数描述

        Args:
            method_func: 方法对象

        Returns:
            str: 函数描述
        """
        import inspect as insp_module

        doc = insp_module.getdoc(method_func)
        if not doc:
            return f"Call the method {method_func.__name__}"

        # 返回第一行作为简短描述
        first_line = doc.split("\n")[0].strip()
        return first_line

    def _execute_tool(self, tool_name: str, arguments: Dict) -> Any:
        """
        执行工具调用

        Args:
            tool_name: 工具名称 (如 "call_text_helper__get_text")
            arguments: 参数字典

        Returns:
            工具执行结果
        """
        # 解析工具名称，找到对应的方法
        # 例如：call_text_helper__get_text -> text_helper.get_text
        if not tool_name.startswith("call_"):
            raise ValueError(f"无效的工具名称：{tool_name}")

        # 移除 "call_" 前缀
        method_full_name = tool_name[5:]  # 去掉 "call_"

        # 使用双下划线分割命名空间和方法名
        parts = method_full_name.split("__", 1)
        if len(parts) == 2:
            namespace = parts[0]
            method_name = parts[1]  # 方法名中可能包含点号，不需要替换
            full_name = f"{namespace}.{method_name}"
        else:
            # 如果没有双下划线，尝试用单下划线分割（向后兼容旧版本）
            # 旧版本格式：call_namespace_method_name -> namespace.method.name
            parts = method_full_name.split("_", 1)
            if len(parts) == 2:
                namespace = parts[0]
                method_name = parts[1].replace("_", ".")
                full_name = f"{namespace}.{method_name}"
            else:
                full_name = method_full_name.replace("_", ".")

        print(f"[工具调用] 工具名：{tool_name} -> 方法：{full_name}")

        # 获取方法
        if not self.plugin_manager:
            raise ValueError("插件管理器未初始化")
        method_func = self.plugin_manager.get_method(full_name)
        if not method_func:
            raise ValueError(f"找不到方法：{full_name}")

        # 执行方法
        result = method_func(**arguments)
        return result

    def _on_response_update(self, new_text: str):
        """接收文本块的回调（在主线程中执行）"""
        import sys
        from IPython import display

        ipython = get_ipython()
        if ipython is not None:
            display.clear_output(wait=True)
            display.display(display.Markdown(new_text))
        print(new_text, end="\n", flush=True)
        # # 如果在 IPython 环境中，使用 IPython 的显示系统
        # if hasattr(self, 'ipython_shell') and self.ipython_shell:
        #     # 使用 IPython 的方式输出到前端
        #     # 注意：在 Qt 控制台中，print 会被重定向到当前活动的输出流

        #     # 确保输出到 IPython 的控制台
        #     if hasattr(sys.stdout, 'write'):
        #         sys.stdout.write(chunk)
        #         sys.stdout.flush()
        #     else:
        #         # 回退到普通 print
        #         print(chunk, end="", flush=True)
        # else:
        #     # 不在 IPython 环境中，直接打印
        #     print(chunk, end="", flush=True)

    def _on_message_recv(self, response: dict):
        """响应完成的回调（在主线程中执行）"""
        print("\n" + "-" * 60)
        print(f"[Agent] 响应完成")

        # 添加助手消息到历史
        self.messages.append(response)

    def _on_error(self, error_msg: str):
        """错误处理的回调（在主线程中执行）"""
        print(error_msg)

    def show_messages(self):
        """
        将消息列表渲染为Markdown形式,调用text_helper里面的接口方法进行显示
        """
        message_strs = []
        for i, msg in enumerate(self.messages):
            msg_new = msg.copy()
            if "content" in msg_new:
                msg_new["content"] = f"..."
            if "reasoning_content" in msg_new:
                msg_new["reasoning_content"] = f"..."
            text = f"""
# {i+1}. {msg['role']}:

## Metadata:

```json
{json.dumps(msg_new, ensure_ascii=False, indent=4)}
```

            """
            text += (f"""               
## Content:
{msg.get('content', '[No content]')}

            """) if "content" in msg else ""
            text += (f"""             
## Reasoning:
{msg.get('reasoning_content', '[No Reasoning Content]')}

            """) if "reasoning_content" in msg else ""

            message_strs.append(text)
        method = self.plugin_manager.get_method(
            "text_helper.render_markdown",
        )
        if method:
            method("\n".join(message_strs))
            logger.info("[LLM Bridge] 消息已渲染为 Markdown 并显示")
        else:
            logger.error(
                "[LLM Bridge] 未找到 text_helper.render_markdown 方法，无法显示消息"
            )


# ==================== Magic 命令注册 ====================


def register_llm_magics(shell, agent: Agent):
    """
    注册 LLM 相关的 magic 命令

    Args:
        shell: IPython shell 实例
        agent: Agent 实例
    """
    from IPython.core.magic import register_line_magic

    # 注册 %ask
    @register_line_magic
    def ask(line):
        """向 LLM 提问（流式输出）"""
        if not line.strip():
            print("用法：%aask <你的问题>")
            return
        agent.ask(line.strip())

    # 注册 %agent_clear
    @register_line_magic
    def agent_clear(line):
        """清除历史对话"""
        agent.clear()
    
    # 注册 %agent_messages
    @register_line_magic
    def agent_messages(line):
        """显示历史对话"""
        agent.show_messages()

    print("[LLM Bridge] 已注册 magic 命令：%ask, %agent_clear, %agent_messages")


# ==================== 初始化函数 ====================


def init_ipython_llm_agent_api(
    ipython_tab: "IPythonConsoleTab", plugin_manager=None, llm_config: Optional[LLMConfig] = None, 
):
    """
    初始化 IPython LLM Agent API

    Args:
        plugin_manager: 插件管理器实例（可选）
        llm_config: LLM 配置（可选）

    Returns:
        Agent: Agent 对象
    """
    # 获取 IPython shell 命名空间
    try:
        from IPython.core.getipython import get_ipython

        shell = get_ipython()

        if shell:
            # 创建 Agent 实例（传入 shell 引用）
            agent = Agent(
                ipython_tab=ipython_tab,
                config=llm_config, plugin_manager=plugin_manager, ipython_shell=shell
            )

            # 将 agent 注入到用户命名空间
            shell.user_ns["agent"] = agent

            # 注册 magic 命令
            register_llm_magics(shell, agent)

            # 注册自省方法，获取所有的能力
            pm = get_plugin_manager()
            pm._register_system_method(
                "list_all_tools", agent._build_mcp_tools, {"enable_mcp": True}, "override"
            )

            print("\n" + "=" * 60)
            print("IPython LLM Agent API 已初始化")
            print("=" * 60)
            print("\n使用方法:")
            print("  agent.ask('问题')       - 向 LLM 提问（流式输出）")
            print("  agent.clear()          - 清除历史对话")
            print("  agent.set_system_prompt('提示词') - 设置系统提示")
            print("  %agent_ask <问题>      - Magic 命令提问")
            print("  %agent_clear           - Magic 命令清除历史")
            print("\n示例:")
            print("  >>> agent.ask('你好，请介绍一下自己')")
            print("  >>> %agent_ask 今天天气如何")
            print("  >>> agent.clear()")
            print("=" * 60 + "\n")
        else:
            print("[警告] 不在 IPython 环境中，无法注入 API")

    except Exception as e:
        print(f"[LLM Bridge] 初始化失败：{e}")
        import traceback

        traceback.print_exc()

    return agent
