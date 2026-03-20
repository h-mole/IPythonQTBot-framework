# IPython LLM Agent 使用指南

## 功能概述

IPython LLM Agent 提供了一个流式输出的对话框架，可以在 IPython 控制台中与 LLM 进行交互式对话。

## 主要特性

1. ✅ **流式输出** - 实时显示 LLM 的响应内容
2. ✅ **历史记忆** - 自动保存对话历史，支持上下文理解
3. ✅ **多 LLM 支持** - 支持 Kimi、OpenAI、智谱等多个提供商
4. ✅ **MCP 工具集成** - 自动集成启用了 MCP 的插件方法
5. ✅ **Magic 命令** - 支持 `%agent_ask` 和 `%agent_clear` 命令

## 快速开始

### 1. 环境准备

确保已安装必要的依赖：

```bash
pip install openai
```

### 2. 配置 API Key

在 `.env` 文件中配置 API Key（项目根目录）：

```bash
API_KEY=your_kimi_api_key_here
```

或者设置环境变量：
- Windows: `set API_KEY=your_kimi_api_key_here`
- Linux/Mac: `export API_KEY=your_kimi_api_key_here`

### 3. 启动应用

运行主程序，IPython 控制台会自动加载 LLM Agent：

```bash
python run_helper_qt.py
```

然后在 IPython 控制台中使用。

## 使用方法

### 方法 1: 使用 agent 对象

```python
# 提问
agent.ask("你好，请介绍一下自己")

# 查看历史对话
print(agent.messages)

# 清除历史对话
agent.clear()

# 设置系统提示词
agent.set_system_prompt("你是一个专业的编程助手")

# 继续对话
agent.ask("Python 中如何实现装饰器？")
```

### 方法 2: 使用 Magic 命令

```ipython
# 提问
%agent_ask 你好，请介绍一下自己

# 清除历史
%agent_clear

# 继续提问
%agent_ask Python 中的装饰器和 Java 中的注解有什么区别
```

## 高级用法

### 1. 自定义 LLM 配置

```python
from app_qt.ipython_llm_bridge import Agent, LLMConfig

# 创建自定义配置
config = LLMConfig(
    provider="kimi",  # 可选："kimi", "openai", "zhipu"
    api_key="your_api_key",  # 不提供则从环境变量读取
    base_url="https://api.moonshot.cn/v1",  # 可选，覆盖默认值
    model="kimi-k2.5"  # 可选，覆盖默认值
)

# 创建 Agent
agent = Agent(config=config)
```

### 2. 多轮对话示例

```python
# 第一轮
agent.ask("我想学习 Python，应该从哪里开始？")

# 第二轮（会记住第一轮的内容）
agent.ask("我已经学会了基础语法，接下来学什么？")

# 第三轮（继续基于上下文）
agent.ask("能推荐一些实战项目吗？")
```

### 3. 结合 MCP 工具使用

如果插件中有方法配置了 `enable_mcp=True`，Agent 会自动调用这些工具：

```python
# 假设 text_helper.get_text 启用了 MCP
agent.ask("请帮我处理一下这段文本，去除所有换行符")

# Agent 会自动调用 text_helper.remove_newlines_api 方法
```

## 配置选项

### 支持的 LLM 提供商

| 提供商 | provider 值 | 默认模型 | 环境变量 |
|--------|------------|---------|---------|
| Kimi | `"kimi"` | `kimi-k2.5` | `API_KEY` |
| OpenAI | `"openai"` | `gpt-3.5-turbo` | `OPENAI_API_KEY` |
| 智谱 AI | `"zhipu"` | `glm-4` | `ZHIPU_API_KEY` |

### 添加新的 LLM 提供商

```python
LLMConfig.PROVIDERS["custom"] = {
    "base_url": "https://your-api.com/v1",
    "model": "your-model",
    "env_key": "CUSTOM_API_KEY"
}

config = LLMConfig(provider="custom")
agent = Agent(config=config)
```

## API 参考

### Agent 类

#### `__init__(config=None, plugin_manager=None)`
初始化 Agent

**参数:**
- `config`: LLMConfig 对象（可选，默认使用 Kimi）
- `plugin_manager`: 插件管理器实例（用于 MCP 工具）

#### `ask(prompt: str)`
向 LLM 提问（流式输出）

**参数:**
- `prompt`: 用户问题字符串

#### `clear()`
清除历史对话

#### `set_system_prompt(system_prompt: str)`
设置系统提示词

**参数:**
- `system_prompt`: 系统提示词

#### `messages: List[Dict[str, str]]`
对话历史列表，每个元素包含：
- `role`: "user", "assistant", 或 "system"
- `content`: 对话内容

### LLMConfig 类

#### `__init__(provider, api_key=None, base_url=None, model=None)`
初始化 LLM 配置

**参数:**
- `provider`: 提供商名称
- `api_key`: API Key（可选，默认从环境变量读取）
- `base_url`: API 基础 URL（可选）
- `model`: 模型名称（可选）

## Magic 命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `%agent_ask` | 向 LLM 提问 | `%agent_ask 你好` |
| `%agent_clear` | 清除对话历史 | `%agent_clear` |

## 故障排除

### 问题 1: "未安装 openai 库"

**解决方案:**
```bash
pip install openai
```

### 问题 2: "未提供 API Key"

**解决方案:**
1. 检查 `.env` 文件中是否有 `API_KEY=...`
2. 或者在创建 Agent 时传入 `api_key` 参数

### 问题 3: 流式输出不显示

**可能原因:**
- Qt 事件循环未正常运行
- IPython 控制台未正确初始化

**解决方案:**
确保在主应用程序中使用 `ipython_console_tab.py` 中提供的完整初始化流程

### 问题 4: MCP 工具未被调用

**检查项:**
1. 确认插件方法在注册时设置了 `enable_mcp=True`
2. 确认插件管理器已正确传递给 Agent
3. 检查方法签名是否能被正确转换为 OpenAI Tool 格式

## 示例代码

### 完整对话流程

```python
from app_qt.ipython_llm_bridge import Agent

# 创建 Agent
agent = Agent()

# 设置角色
agent.set_system_prompt("你是一个专业的 Python 编程助手")

# 开始对话
agent.ask("什么是装饰器？")
# 等待回答...

agent.ask("能给我一个实际的例子吗？")
# 等待回答...

agent.ask("这个例子中使用了哪些 Python 特性？")
# 等待回答...

# 清除历史，开始新话题
agent.clear()
agent.ask("现在我们来聊聊 Web 开发吧")
```

### 使用 Magic 命令

```ipython
In [1]: %agent_ask 请用 Python 写一个快速排序

Out[1]: 好的，下面是一个 Python 实现的快速排序函数：
        
        def quick_sort(arr):
            if len(arr) <= 1:
                return arr
            pivot = arr[len(arr) // 2]
            left = [x for x in arr if x < pivot]
            middle = [x for x in arr if x == pivot]
            right = [x for x in arr if x > pivot]
            return quick_sort(left) + middle + quick_sort(right)
        
        这个实现使用了分治法...

In [2]: %agent_ask 解释一下第 4 行的作用

Out[2]: 第 4 行 `pivot = arr[len(arr) // 2]` 的作用是选择基准值...
```

## 最佳实践

1. **合理设置系统提示词** - 明确的系统提示可以提高回答质量
2. **适时清除历史** - 当话题转换时使用 `agent.clear()`
3. **利用历史记忆** - 连续提问可以获得更好的上下文理解
4. **结合 MCP 工具** - 对于可以程序化解决的任务，让 Agent 调用工具

## 更新日志

### v1.0.0 (2026-03-20)
- ✅ 初始版本发布
- ✅ 支持流式输出
- ✅ 支持历史记忆
- ✅ 支持多 LLM 提供商
- ✅ 集成 MCP 工具
- ✅ 支持 Magic 命令

## 开发者

如有问题或建议，请联系开发团队。
