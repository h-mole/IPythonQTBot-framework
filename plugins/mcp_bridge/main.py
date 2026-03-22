"""
MCP Bridge Plugin - MCP 工具桥接插件

功能：
1. 从 JSON 配置文件导入 MCP 服务器配置
2. 连接 MCP 服务器并获取工具列表
3. 将 MCP 工具映射为 LLM 可调用的 tools
4. 支持通过 IPython LLM Bridge 使用 MCP 工具
"""

import logging
import threading
import os
import json
import asyncio
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from pathlib import Path

from app_qt.utils import wrap_async_in_sync, AsyncThreadRunner
from app_qt.configs import PLUGIN_DATA_DIR
if TYPE_CHECKING:
    from app_qt.plugin_manager import PluginManager

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.client.sse import sse_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("[MCP Bridge] 警告：未安装 mcp 库，请运行：pip install mcp")

logger = logging.getLogger("mcp_bridge")


class MCPServerManager:
    """MCP 服务器管理器"""
    
    def __init__(self):
        self.servers: Dict[str, Dict] = {}
        self.sessions: Dict[str, Any] = {}
        self.tools_cache: Dict[str, List[Dict]] = {}
        self.client_contexts: Dict[str, Any] = {}  # 存储客户端上下文
        
        # 【核心修改】使用 AsyncThreadRunner 维护一个常驻的 EventLoop
        # 这个 Loop 将负责维持所有 MCP 连接，防止 Loop 提前关闭
        self.runner = AsyncThreadRunner()

    def load_config(self, config_path: str) -> bool:
        """
        从 JSON 文件加载 MCP 服务器配置

        Args:
            config_path: 配置文件路径

        Returns:
            bool: 是否加载成功
        """
        try:
            if not os.path.exists(config_path):
                print(f"[MCP Bridge] 配置文件不存在：{config_path}")
                return False

            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            mcp_servers = config.get("mcpServers", {})

            for server_name, server_config in mcp_servers.items():
                self.servers[server_name] = server_config
                print(f"[MCP Bridge] 已加载服务器配置：{server_name}")

            return True
        except Exception as e:
            print(f"[MCP Bridge] 加载配置失败：{e}")
            import traceback
            traceback.print_exc()
            return False

    async def connect_to_server(self, server_name: str) -> bool:
        """
        连接到 MCP 服务器

        Args:
            server_name: 服务器名称

        Returns:
            bool: 是否连接成功
        """
        if server_name not in self.servers:
            logger.error(f"[MCP Bridge] 服务器不存在：{server_name}")
            return False

        server_config = self.servers[server_name]
        server_type = server_config.get("type", "stdio")

        try:
            if server_type.lower() in ("streamable-http", "streamablehttp"):
                # HTTP 流式连接
                url = server_config.get("url")
                headers = server_config.get("headers", {})

                if not url:
                    logger.error(f"[MCP Bridge] URL 未配置：{server_name}")
                    return False

                # 创建 HTTP 客户端并初始化会话
                client_ctx = streamablehttp_client(url=url, headers=headers)
                # 进入客户端上下文
                streams = await client_ctx.__aenter__()
                read_stream, write_stream = streams[0], streams[1]

                # 创建并初始化会话
                session = ClientSession(read_stream, write_stream)
                await session.__aenter__()
                await session.initialize()

                # 保存会话和客户端上下文
                self.sessions[server_name] = session
                self.client_contexts[server_name] = client_ctx

                # 获取工具列表并缓存
                tools_response = await session.list_tools()
                self.tools_cache[server_name] = tools_response.tools
                print(
                    f"[MCP Bridge] 已连接到服务器：{server_name}，共 {len(tools_response.tools)} 个工具"
                )
                return True
            elif server_type == "http":
                # HTTP 方式连接（使用 streamable HTTP 客户端）
                url = server_config.get("url")
                headers = server_config.get("headers", {})

                if not url:
                    logger.error(f"[MCP Bridge] URL 未配置：{server_name}")
                    return False

                # 创建 HTTP 客户端并初始化会话
                client_ctx = streamablehttp_client(url=url, headers=headers)
                # 进入客户端上下文
                streams = await client_ctx.__aenter__()
                read_stream, write_stream = streams[0], streams[1]

                # 创建并初始化会话
                session = ClientSession(read_stream, write_stream)
                await session.__aenter__()
                await session.initialize()

                # 保存会话和客户端上下文
                self.sessions[server_name] = session
                self.client_contexts[server_name] = client_ctx

                # 获取工具列表并缓存
                tools_response = await session.list_tools()
                self.tools_cache[server_name] = tools_response.tools
                print(
                    f"[MCP Bridge] 已连接到服务器：{server_name}，共 {len(tools_response.tools)} 个工具"
                )
                return True
            elif server_type == "sse":
                # SSE 方式连接
                url = server_config.get("url")
                headers = server_config.get("headers", {})

                if not url:
                    logger.error(f"[MCP Bridge] URL 未配置：{server_name}")
                    return False

                # 创建 SSE 客户端并初始化会话
                client_ctx = sse_client(url=url, headers=headers)
                # 进入客户端上下文
                streams = await client_ctx.__aenter__()
                read_stream, write_stream = streams[0], streams[1]

                # 创建并初始化会话
                session = ClientSession(read_stream, write_stream)
                await session.__aenter__()
                await session.initialize()

                # 保存会话和客户端上下文
                self.sessions[server_name] = session
                self.client_contexts[server_name] = client_ctx

                # 获取工具列表并缓存
                tools_response = await session.list_tools()
                self.tools_cache[server_name] = tools_response.tools
                print(
                    f"[MCP Bridge] 已连接到服务器：{server_name}，共 {len(tools_response.tools)} 个工具"
                )
                return True

            elif server_type == "stdio":
                # 标准输入输出连接
                command = server_config.get("command")
                args = server_config.get("args", [])
                env = server_config.get("env", {})

                if not command:
                    logger.error(f"[MCP Bridge] 命令未配置：{server_name}")
                    return False

                server_params = StdioServerParameters(
                    command=command, args=args, env=env
                )

                # 获取客户端上下文管理器
                client_ctx = stdio_client(server_params)
                # 进入客户端上下文
                streams = await client_ctx.__aenter__()
                read, write = streams

                # 创建并初始化会话
                session = ClientSession(read, write)
                await session.__aenter__()
                await session.initialize()

                # 保存会话和客户端上下文
                self.sessions[server_name] = session
                self.client_contexts[server_name] = client_ctx

                # 获取工具列表并缓存
                tools_response = await session.list_tools()
                self.tools_cache[server_name] = tools_response.tools
                print(
                    f"[MCP Bridge] 已连接到服务器：{server_name}，共 {len(tools_response.tools)} 个工具"
                )
                return True
            else:
                logger.error(f"[MCP Bridge] 不支持的服务器类型：{server_type}")
                return False

        except Exception as e:
            logger.error(f"[MCP Bridge] 连接服务器失败：{server_name}, 错误：{e}")
            import traceback
            traceback.print_exc()
            return False

    async def disconnect_from_server(self, server_name: str) -> bool:
        """
        断开与 MCP 服务器的连接

        Args:
            server_name: 服务器名称

        Returns:
            bool: 是否断开成功
        """
        if server_name not in self.sessions:
            return True

        try:
            # 先关闭会话
            session = self.sessions[server_name]
            await session.__aexit__(None, None, None)
            del self.sessions[server_name]

            # 再关闭客户端上下文
            if server_name in self.client_contexts:
                client_ctx = self.client_contexts[server_name]
                await client_ctx.__aexit__(None, None, None)
                del self.client_contexts[server_name]

            if server_name in self.tools_cache:
                del self.tools_cache[server_name]

            logger.info(f"[MCP Bridge] 已断开服务器：{server_name}")
            return True
        except Exception as e:
            logger.error(f"[MCP Bridge] 断开服务器失败：{server_name}, 错误：{e}")
            return False

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """
        获取所有已连接服务器的工具列表

        Returns:
            List[Dict]: 工具列表
        """
        all_tools = []

        for server_name, tools in self.tools_cache.items():
            for tool in tools:
                # 将 Tool 对象转换为字典
                if hasattr(tool, "__dict__"):
                    # 如果是对象，转换为字典
                    tool_dict = {
                        "name": getattr(tool, "name", "unknown"),
                        "description": getattr(tool, "description", ""),
                        "inputSchema": getattr(tool, "inputSchema", {}),
                    }
                elif isinstance(tool, dict):
                    # 如果已经是字典，直接使用
                    tool_dict = tool.copy()
                else:
                    # 其他情况，尝试转换为字典
                    tool_dict = dict(tool) if hasattr(tool, "__iter__") else {}

                # 使用 getattr 安全访问属性，兼容 dict 和对象
                tool_name = tool_dict.get("name", "unknown")

                # 添加服务器前缀以区分不同服务器的工具
                tool_dict["name"] = f"{server_name}__{tool_name}"
                tool_dict["server"] = server_name

                all_tools.append(tool_dict)

        return all_tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        调用 MCP 工具

        Args:
            tool_name: 工具名称（带服务器前缀）
            arguments: 参数字典

        Returns:
            Any: 工具执行结果
        """
        # 解析工具名称
        parts = tool_name.split("__", 1)
        if len(parts) != 2:
            raise ValueError(f"无效的工具名称：{tool_name}")

        server_name = parts[0]
        actual_tool_name = parts[1]

        if server_name not in self.sessions:
            raise ValueError(f"服务器未连接：{server_name}")

        session = self.sessions[server_name]

        # 调用工具
        result = await session.call_tool(actual_tool_name, arguments)
        return result


class MCPBridgeWidget:
    """MCP Bridge 功能组件（无 UI）"""

    def __init__(self, plugin_manager=None):
        super().__init__()
        self.plugin_manager: "PluginManager" = plugin_manager
        self.server_manager = MCPServerManager()
        self.config_path = self._get_config_path()

        # 自动加载配置
        self._auto_load_config()

    def _get_config_path(self) -> str:
        """获取配置文件路径"""
        # ~/IPythonQTBot/mcp_bridge/config.json
        base_dir = os.path.join(PLUGIN_DATA_DIR, "mcp_bridge")
        os.makedirs(base_dir, exist_ok=True)
        config_path = os.path.join(base_dir, "config.json")
        return config_path

    def _auto_load_config(self):
        """自动加载配置文件"""
        if os.path.exists(self.config_path):
            self.server_manager.load_config(self.config_path)
            logger.info(f"[MCP Bridge] 已自动加载配置：{self.config_path}")
        else:
            logger.error(f"[MCP Bridge] 配置文件不存在，请创建：{self.config_path}")
            # 创建示例配置
            self._create_sample_config()

    def _create_sample_config(self):
        """创建示例配置文件"""
        sample_config = {
            "mcpServers": {
                "web-search-prime": {
                    "type": "streamable-http",
                    "url": "https://open.bigmodel.cn/api/mcp/web_search_prime/mcp",
                    "headers": {"Authorization": "Bearer your_api_key"},
                }
            }
        }

        try:
            config_dir = os.path.dirname(self.config_path)
            os.makedirs(config_dir, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(sample_config, f, indent=2, ensure_ascii=False)
            logger.info(f"[MCP Bridge] 已创建示例配置：{self.config_path}")
        except Exception as e:
            logger.error(f"[MCP Bridge] 创建示例配置失败：{e}")

    def load_mcp_config(self, config_path: str) -> bool:
        """
        手动加载 MCP 配置

        Args:
            config_path: 配置文件路径

        Returns:
            bool: 是否加载成功
        """
        return self.server_manager.load_config(config_path)

    async def connect_all_servers(self) -> bool:
        """
        连接所有配置的服务器

        Returns:
            bool: 是否全部连接成功
        """
        total_count = len(self.server_manager.servers)
        logger.info(f"[MCP Bridge] 正在连接 {total_count} 个服务器...")
        
        # 并发连接所有服务器
        tasks = [
            self.server_manager.connect_to_server(server_name)
            for server_name in self.server_manager.servers.keys()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        success_count = 0
        for server_name, result in zip(self.server_manager.servers.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"[MCP Bridge] 连接服务器异常：{server_name}, 错误：{result}")
            elif result:
                success_count += 1
            else:
                logger.error(f"[MCP Bridge] 连接服务器失败：{server_name}")

        logger.info(f"[MCP Bridge] 连接完成：{success_count}/{total_count}")
        self.register_mcp_tools()
        logger.info("[MCP Bridge] 已注册 MCP 外部工具为回调")
        return success_count == total_count

    async def demo_tool(self, kwargs):
        print(kwargs)
        return "demo_tool called, 天气晴,温度10度"

    def _create_wrap_func(self, tool_name: str):
        def wrapper(**kwargs):
            # 【核心修改】使用 server_manager 持有的 runner 提交任务
            # 这样保证了工具调用任务运行在 Session 所在的同一个 EventLoop 中
            # 避免了 "Event loop is closed" 的错误
            print("已开始工具调用...", tool_name, kwargs)
            return self.server_manager.runner.submit(
                self.server_manager.call_tool(tool_name, kwargs)
            )

        return wrapper

    def register_mcp_tools(self):
        """
        将 MCP 工具转换为文档函数, 调用函数的时候就是对应的call_tool

        Args:
            tools: MCP 工具列表

        Returns:
            List[Dict]: 文档函数列表
        """
        assert self.plugin_manager is not None

        all_tools = self.server_manager.get_all_tools()
        # llm_tools = []

        for mcp_tool in all_tools:
            # 转换为 OpenAI Tool 格式
            llm_tool_info = {
                "type": "function",
                "function": {
                    "name": f"call_mcp_bridge__{mcp_tool['name'].replace('.', '__')}",
                    "description": mcp_tool.get("description", ""),
                    "parameters": mcp_tool.get(
                        "inputSchema", {"type": "object", "properties": {}, "required": []}
                    ),
                },
            }

            self.plugin_manager.register_method(
                "mcp_bridge",
                mcp_tool["name"],
                self._create_wrap_func(mcp_tool["name"]),
                extra_data={"enable_mcp": True},
                llm_tool_info=llm_tool_info,
            )

    def get_mcp_tools_for_llm(self) -> List[Dict[str, Any]]:
        """
        获取 MCP 工具并转换为 LLM Tool 格式

        Returns:
            List[Dict]: OpenAI Tool 格式的工具列表
        """
        all_tools = self.server_manager.get_all_tools()
        llm_tools = []

        for mcp_tool in all_tools:
            # 转换为 OpenAI Tool 格式
            llm_tool = {
                "type": "function",
                "function": {
                    "name": f"call_mcp__{mcp_tool['name'].replace('.', '__')}",
                    "description": mcp_tool.get("description", ""),
                    "parameters": mcp_tool.get(
                        "inputSchema", {"type": "object", "properties": {}, "required": []}
                    ),
                },
            }
            llm_tools.append(llm_tool)

        return llm_tools

    def list_servers(self) -> List[str]:
        """
        列出所有已配置的服务器

        Returns:
            List[str]: 服务器名称列表
        """
        return list(self.server_manager.servers.keys())

    def list_connected_servers(self) -> List[str]:
        """
        列出所有已连接的服务器

        Returns:
            List[str]: 服务器名称列表
        """
        return list(self.server_manager.sessions.keys())

    def get_tools_info(self, detailed: bool = False) -> str:
        """
        获取工具信息文本

        Args:
            detailed: 是否显示详细信息

        Returns:
            str: 工具信息文本
        """
        tools = self.get_mcp_tools_for_llm()

        if not tools:
            return "[MCP Bridge] 暂无可用工具\n"

        lines = [f"[MCP Bridge] 可用工具 ({len(tools)} 个):\n"]
        logger.info("".join(lines))

        for i, tool in enumerate(tools, 1):
            func = tool["function"]
            lines.append(f"{i}. {func['name']}")
            if detailed:
                lines.append(f"   描述：{func['description']}")
                params = func["parameters"].get("properties", {})
                if params:
                    lines.append("   参数:")
                    for param_name, param_info in params.items():
                        param_type = param_info.get("type", "any")
                        param_desc = param_info.get("description", "")
                        lines.append(
                            f"     - {param_name} ({param_type}): {param_desc}"
                        )
            else:
                desc_text = func['description'][:100] if func['description'] else "无描述"
                lines.append(f"   {desc_text}...")
            lines.append("")

        return "\n".join(lines)


# ==================== 插件入口函数 ====================

def load_plugin(plugin_manager: "PluginManager"):
    """
    插件加载入口函数

    Args:
        plugin_manager: 插件管理器实例

    Returns:
        dict: 包含插件组件的字典
    """
    logger.info("[MCP Bridge] 正在加载 MCP Bridge 插件...")

    if not MCP_AVAILABLE:
        logger.error("[MCP Bridge] 错误：MCP 库未安装，插件无法加载")
        return None

    # 创建 widget 实例
    mcp_bridge = MCPBridgeWidget(plugin_manager=plugin_manager)

    # 注册暴露的方法到全局域
    plugin_manager.register_method(
        "mcp_bridge", "load_mcp_config", mcp_bridge.load_mcp_config,
    )
    plugin_manager.register_method(
        "mcp_bridge", "get_mcp_tools", mcp_bridge.get_mcp_tools_for_llm,
    )
    plugin_manager.register_method(
        "mcp_bridge", "list_servers", mcp_bridge.list_servers
    )
    plugin_manager.register_method(
        "mcp_bridge", "get_tools_info", mcp_bridge.get_tools_info,
    )

    # 【核心修改】使用 runner 提交连接任务
    # 这能确保 connect_all_servers 在 runner 的 Loop 中执行
    # 从而使 Session 与 runner 的 Loop 绑定
    
    def connect_servers_task():
        mcp_bridge.server_manager.runner.submit(mcp_bridge.connect_all_servers())
    
    # 启动后台线程触发连接（不阻塞插件加载）
    threading.Thread(target=connect_servers_task, daemon=True).start()
    
    print("[MCP Bridge] MCP Bridge 插件加载完成")
    return {
        "widget": mcp_bridge,
        "namespace": "mcp_bridge",
    }


def unload_plugin(plugin_manager):
    """
    插件卸载回调

    Args:
        plugin_manager: 插件管理器实例
    """
    print("[MCP Bridge] 正在卸载 MCP Bridge 插件...")
    # 清理资源、断开连接等
    print("[MCP Bridge] MCP Bridge 插件卸载完成")
