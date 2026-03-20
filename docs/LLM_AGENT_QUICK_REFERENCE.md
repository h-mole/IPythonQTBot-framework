# IPython LLM Agent 快速参考

## 🚀 一分钟上手

### 1. 环境准备
```bash
pip install openai ipython
```

### 2. 配置 API Key
在项目根目录创建 `.env` 文件：
```bash
API_KEY=sk-your-api-key-here
```

### 3. 启动并使用
```bash
# 方式 1: 使用快速启动脚本
python quickstart_llm.py

# 方式 2: 运行主程序
python run_helper_qt.py
# 然后切换到 IPython 控制台标签页
```

---

## 💬 核心命令

### Python API
```python
# 提问（流式输出）
agent.ask("你好，请介绍一下自己")

# 清除历史对话
agent.clear()

# 设置系统提示词
agent.set_system_prompt("你是一个专业的 Python 助手")

# 查看历史消息
print(agent.messages)

# 查看当前配置
print(agent.config.provider)
print(agent.config.model)
```

### Magic 命令
```ipython
# 提问
%agent_ask 什么是 Python 的装饰器？

# 继续提问（会记住上下文）
%agent_ask 能给我一个实际的例子吗？

# 清除历史
%agent_clear
```

---

## 🎯 常用场景

### 场景 1: 单次问答
```python
agent.ask("Python 中如何实现单例模式？")
```

### 场景 2: 多轮对话
```python
# 第一轮
agent.ask("我想学习数据分析，应该从哪里开始？")

# 第二轮（会记住第一轮）
agent.ask("我已经学会了 pandas，接下来学什么？")

# 第三轮（继续上下文）
agent.ask("能推荐一些实战项目吗？")
```

### 场景 3: 角色设定
```python
agent.set_system_prompt("你是一个资深的代码审查员，专注于代码质量和最佳实践")
agent.ask("请审查这段代码：[你的代码]")
```

### 场景 4: 切换话题
```python
# 第一个话题
agent.ask("什么是机器学习？")
# ... 对话 ...

# 清除并开始新话题
agent.clear()
agent.ask("现在我们聊聊 Web 开发")
```

---

## 🔧 高级配置

### 更换 LLM 提供商

```python
from app_qt.ipython_llm_bridge import Agent, LLMConfig

# 使用 Kimi（默认）
config = LLMConfig(provider="kimi", model="kimi-k2.5")
agent = Agent(config=config)

# 使用 OpenAI
config = LLMConfig(
    provider="openai", 
    model="gpt-3.5-turbo",
    api_key="sk-xxx"  # 不提供则从 OPENAI_API_KEY 读取
)
agent = Agent(config=config)

# 使用智谱 AI
config = LLMConfig(
    provider="zhipu",
    model="glm-4",
    api_key="xxx.xxx"  # 从 ZHIPU_API_KEY 读取
)
agent = Agent(config=config)
```

### 自定义 API 地址

```python
config = LLMConfig(
    provider="kimi",
    base_url="https://your-custom-api.com/v1",  # 自定义 API 地址
    model="custom-model"
)
agent = Agent(config=config)
```

---

## 📊 查看状态

```python
# 查看对话历史数量
print(f"当前对话数：{len(agent.messages)}")

# 查看所有历史消息
for i, msg in enumerate(agent.messages):
    print(f"{i+1}. [{msg['role']}] {msg['content'][:50]}...")

# 查看当前配置
print(f"提供商：{agent.config.provider}")
print(f"模型：{agent.config.model}")
print(f"API 地址：{agent.config.base_url}")
```

---

## ⚠️ 常见问题

### Q1: "未安装 openai 库"
```bash
pip install openai
```

### Q2: "未提供 API Key"
检查 `.env` 文件是否存在且包含正确的 API_KEY

### Q3: 如何停止正在输出的内容？
目前会持续输出直到完成，可以等待输出结束

### Q4: 对话历史有上限吗？
没有硬性限制，但建议定期使用 `agent.clear()` 清理

---

## 🎨 使用技巧

### 技巧 1: 利用上下文
```python
# 不要这样（每次都重新解释）
agent.ask("什么是 Python?")
agent.ask("什么是装饰器？")
agent.ask("什么是生成器？")

# 要这样（利用上下文）
agent.ask("我想学习 Python")
agent.ask("什么是装饰器？")  # Agent 知道你在问 Python
agent.ask("那生成器呢？")     # 继续 Python 话题
```

### 技巧 2: 明确系统提示
```python
# 模糊的提示
agent.set_system_prompt("帮助我编程")

# 明确的提示
agent.set_system_prompt(
    "你是一个资深的 Python 后端工程师，"
    "擅长 Django 和 FastAPI，"
    "回答要包含代码示例和最佳实践"
)
```

### 技巧 3: 分步提问
```python
# 不要一次性问太多
agent.ask("如何从零开始构建一个完整的电商网站，包括前端、后端、数据库、部署？")

# 分步骤提问
agent.ask("电商网站的数据库应该如何设计？")
# ... 讨论数据库 ...
agent.ask("后端 API 应该如何架构？")
# ... 讨论后端 ...
agent.ask("前端用什么框架比较好？")
# ... 讨论前端 ...
```

---

## 📚 相关文档

- **详细使用指南**: [docs/llm_agent_usage.md](docs/llm_agent_usage.md)
- **开发总结**: [docs/llm_agent_development_summary.md](docs/llm_agent_development_summary.md)
- **测试脚本**: [demos/test_llm_bridge.py](demos/test_llm_bridge.py)
- **演示脚本**: [demos/llm_agent_demo.py](demos/llm_agent_demo.py)

---

## 🔗 快捷键参考

| 操作 | 命令 | 说明 |
|------|------|------|
| 提问 | `agent.ask("问题")` | 流式输出 |
| 提问（快捷） | `%agent_ask 问题` | Magic 命令 |
| 清除历史 | `agent.clear()` | 重置对话 |
| 清除历史（快捷） | `%agent_clear` | Magic 命令 |
| 设置提示词 | `agent.set_system_prompt("...")` | 定义角色 |
| 查看历史 | `print(agent.messages)` | 显示所有消息 |
| 查看配置 | `print(agent.config)` | 显示当前配置 |

---

**版本**: v1.0.0  
**更新日期**: 2026-03-20  
**支持提供商**: Kimi, OpenAI, 智谱 AI
