import asyncio
import os
import shutil
from dotenv import load_dotenv

# LangChain / LangGraph 导入
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

# MCP 客户端导入
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_core.tools import tool

load_dotenv()

async def run_agent_demo():
    # 1. 配置服务器连接参数
    # 我们直接指向刚才写的 server 文件
    server_params = StdioServerParameters(
        command="python",
        args=["weather_server.py"], # 确保路径正确
        env=os.environ.copy()
    )

    print("🔗 正在连接到 US Weather MCP 服务器...")

    # 2. 建立 MCP 连接并转换为 LangChain 工具
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化
            await session.initialize()
            
            # 获取服务器上的工具列表
            tools_list = await session.list_tools()
            print(f"✅ 发现工具: {[t.name for t in tools_list.tools]}")

            # 3. 动态包装 MCP 工具为 LangChain 工具
            # 这里我们需要创建一个 LangChain 兼容的 Tool 列表
            langchain_tools = []
            
            for mcp_tool in tools_list.tools:
                # 这是一个闭包，用于捕获当前的 tool_name
                async def make_tool_func(t_name=mcp_tool.name):
                    @tool(t_name)
                    async def dynamic_tool(query: str):
                        """Dynamic wrapper for MCP tool"""
                        return await session.call_tool(t_name, arguments={"city_query": query})
                    return dynamic_tool
                
                # 构建工具实例
                lc_tool = await make_tool_func()
                # 更新工具描述以匹配 MCP 定义
                lc_tool.description = mcp_tool.description
                langchain_tools.append(lc_tool)

            # 4. 构建 LangGraph Agent
            # 使用 GPT-4o 或 GPT-3.5
            # llm = ChatOpenAI(model="gemini-3-pro-preview", temperature=0)
            llm = ChatOpenAI(
                # 商家支持很多模型，你可以试着用 "gpt-4o"，
                # 或者用商家列表里的 "gemini-2.5-pro" (通常更便宜且支持长文本)
                model="gpt-4o", 
                temperature=0,
                # 👇【核心修改】必须加上这行，指向商家的地址
                base_url="https://max.openai365.top/v1",
                api_key=os.environ["OPENAI_API_KEY"] # 确保这里读取的是.env里的新key
            )
            
            # create_react_agent 自动处理工具调用循环
            agent_executor = create_react_agent(llm, langchain_tools)

            print("\n🤖 Agent 已就绪。开始查询...\n")

            # 5. 执行查询测试
            # 测试用例 1: 简单查询
            query1 = "Check the weather in Santa Clara, CA."
            print(f"用户: {query1}")
            
            async for chunk in agent_executor.astream(
                {"messages": [HumanMessage(content=query1)]}, 
                stream_mode="values"
            ):
                # 打印最后一条消息的内容
                last_msg = chunk["messages"][-1]
                if last_msg.type == "ai" and last_msg.tool_calls:
                    print(f"👉 助手决定调用工具: {last_msg.tool_calls[0]['name']}")
                elif last_msg.type == "tool":
                    print("📦 工具返回数据 (已隐藏详细 JSON)")
                elif last_msg.type == "ai":
                    print(f"💬 助手回答: {last_msg.content}")

            print("-" * 50)

            # 测试用例 2: 复杂多地查询
            query2 = "Compare the temperature in New York and Miami right now. Which one is hotter?"
            print(f"\n用户: {query2}")
            
            async for chunk in agent_executor.astream(
                {"messages": [HumanMessage(content=query2)]}, 
                stream_mode="values"
            ):
                if chunk["messages"][-1].type == "ai" and not chunk["messages"][-1].tool_calls:
                     print(f"💬 助手回答: {chunk['messages'][-1].content}")

if __name__ == "__main__":
    # 确保是在当前目录下运行，或者修改 path
    asyncio.run(run_agent_demo())