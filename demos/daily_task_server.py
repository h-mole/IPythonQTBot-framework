import os
import json
import asyncio
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

# 1. 配置 Kimi API (OpenAI 兼容格式)
# 建议将 API Key 存入环境变量
load_dotenv()

client = OpenAI(
    api_key=os.getenv("API_KEY"), # 请替换为您的 API Key
    base_url="https://api.moonshot.cn/v1"
)

# 2. 配置 MCP Server 路径
# 假设您上一轮的 MCP Server 文件名为 daily_task_server.py
server_params = StdioServerParameters(
    command="python",
    args=["mcp_demo.py"], 
)

MODEL="kimi-k2.5"

async def run_chat_loop():
    print("正在连接 MCP Server...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 3. 获取 MCP 工具列表并转换为 OpenAI Tools 格式
            mcp_tools = await session.list_tools()
            openai_tools = []
            
            print(f"已发现工具: {[t.name for t in mcp_tools.tools]}")
            
            # 将 MCP 工具定义转换为 OpenAI 能理解的格式
            for tool in mcp_tools.tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                })

            messages = [
                {"role": "system", "content": "你是一个高效的助手，可以管理用户的每日任务。请根据用户需求调用工具。"}
            ]

            print("\n助手已就绪 (输入 'quit' 退出)...")
            
            while True:
                user_input = input("你: ")
                if user_input.lower() == "quit":
                    break
                
                messages.append({"role": "user", "content": user_input})

                # 4. 调用智谱清言 API
                response = client.chat.completions.create(
                    model=MODEL, # 使用智谱的模型名称
                    messages=messages,
                    tools=openai_tools,
                    tool_choice="auto"
                )

                assistant_message = response.choices[0].message
                messages.append(assistant_message)

                # 5. 处理工具调用 (如果模型决定调用)
                if assistant_message.tool_calls:
                    for tool_call in assistant_message.tool_calls:
                        func_name = tool_call.function.name
                        func_args = json.loads(tool_call.function.arguments)
                        
                        print(f"系统: 正在调用工具 {func_name}...")
                        
                        # 6. 通过 MCP 协议执行工具
                        result = await session.call_tool(func_name, arguments=func_args)
                        
                        # 提取工具返回的文本内容
                        tool_content = result.content[0].text

                        # 7. 将工具结果回传给模型进行最终总结
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_content
                        })
                    
                    # 再次调用模型，让它根据工具结果生成回复
                    final_response = client.chat.completions.create(
                        model=MODEL,
                        messages=messages,
                        tools=openai_tools
                    )
                    final_msg = final_response.choices[0].message
                    print(f"模型: {final_msg.content}")
                    messages.append(final_msg)
                else:
                    # 如果没有工具调用，直接输出回复
                    print(f"模型: {assistant_message.content}")

if __name__ == "__main__":
    asyncio.run(run_chat_loop())
