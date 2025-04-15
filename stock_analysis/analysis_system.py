# analysis_system.py
import os
import asyncio
from langchain.llms.base import LLM
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_mcp_adapters.client import MultiServerMCPClient
import schedule
import time
import pandas as pd
from dotenv import load_dotenv
import requests
from typing import Optional, List, Dict, Any
from langchain_openai import ChatOpenAI
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # 从环境变量获取OpenAI密钥
OPENAI_MODEL = "gpt-3.5-turbo"

llm = None
if OPENAI_API_KEY:
    llm = ChatOpenAI(api_key=OPENAI_API_KEY, model=OPENAI_MODEL, temperature=0)
else:
    # 如果没有OpenAI密钥，则使用一个占位的简单LLM或抛出警告
    from langchain.llms import OpenAI  # 备用使用OpenAI或其他模型
    print("警告：未提供OpenAI API Key，请设置OPENAI_API_KEY环境变量。")
    exit(1)  # 终止程序，因为没有API密钥无法继续

# 启动并连接 MCP 股票数据服务
# 使用 MultiServerMCPClient 同时启动本地的 stock_server MCP 服务
mcp_servers = {
    "stock": {
        "command": "python",
        "args": ["stock_server.py"]  # 确保该脚本在相同目录下
    }
}
client = MultiServerMCPClient(mcp_servers)
# 上下文管理器方式启动异步MCP客户端
async def start_mcp_client():
    await client.__aenter__()  # 手动调用异步上下文的进入
# 启动MCP客户端（需要在事件循环中运行）
asyncio.get_event_loop().run_until_complete(start_mcp_client())

# 从MCP客户端获取工具列表
tools = client.get_tools()  # 包含stock_server提供的所有工具

from langchain.agents import initialize_agent, AgentType

# 创建基于ReAct模式的智能代理
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True
)

# 定义每日分析报告生成函数
def run_daily_analysis():
    """每日自动运行的分析任务：获取数据并生成Excel报告。"""
    print("执行每日分析任务...")
    try:
        # 1. 获取当日市场整体资金流入情况和热点股票
        top_inflows = agent.run("请获取今日主力资金流入最多的5只股票，并列出它们的净流入额。")
        # 2. 获取关注股票列表的基本面与资金数据
        focus_stocks = ["600519", "601398", "000001"]  # 示例股票代码列表（茅台，工商银行，平安银行）
        fundamentals_list = []
        flows_list = []
        for code in focus_stocks:
            try:
                # 调用工具获取数据
                fund_data = client.invoke_tool("get_fundamentals", {"stock_code": code})
                flow_data = client.invoke_tool("get_capital_flow", {"stock_code": code})
                fundamentals_list.append(fund_data)
                flows_list.append(flow_data)
            except Exception as e:
                print(f"获取股票{code}数据失败: {e}")
                fundamentals_list.append({"stock": code, "error": str(e)})
                flows_list.append({"stock": code, "error": str(e)})
                
        # 3. 获取市场新闻摘要
        news_summary = agent.run("请获取几条今天的重要财经新闻。")
        
        # 4. 综合以上数据生成分析结论
        analysis_prompt = f"""
        基于以下数据，生成一个简短的市场分析摘要：
        
        1. 资金流入前5的股票：{top_inflows}
        2. 关注股票基本面：{fundamentals_list}
        3. 关注股票资金流：{flows_list}
        4. 今日财经新闻：{news_summary}
        
        请提供一个简洁的市场分析，包括市场热点、资金流向和投资建议。
        """
        market_analysis = agent.run(analysis_prompt)

        # 5. 生成Excel报表
        today = time.strftime("%Y%m%d")
        report_file = f"A股智能分析报告_{today}.xlsx"
        
        with pd.ExcelWriter(report_file, engine='openpyxl') as writer:
            # 将资金流入排名写入Sheet1
            if isinstance(top_inflows, str):
                # 如果agent返回文本，我们需要解析出结构；此处假设top_inflows是文本，简单处理
                top_inflows_data = eval(top_inflows) if top_inflows.strip().startswith("[") else []
            else:
                top_inflows_data = top_inflows
            df_flows = pd.DataFrame(top_inflows_data, columns=["股票", "净流入(亿元)"])
            df_flows.to_excel(writer, index=False, sheet_name="资金流入排行")
            
            # 基本面数据写入Sheet2
            df_fund = pd.DataFrame(fundamentals_list)
            df_fund.to_excel(writer, index=False, sheet_name="关注股票基本面")
            
            # 资金流数据写入Sheet3
            df_flow_detail = pd.DataFrame(flows_list)
            df_flow_detail.to_excel(writer, index=False, sheet_name="关注股票资金流")
            
            # 新闻及分析写入Sheet4
            df_news = pd.DataFrame({"新闻摘要": news_summary if isinstance(news_summary, list) else [news_summary]})
            df_news.to_excel(writer, index=False, sheet_name="新闻摘要")
            
            # 分析结论写入Sheet5（将整段文字放在单元格A1）
            analysis_df = pd.DataFrame({"分析报告": [market_analysis]})
            analysis_df.to_excel(writer, index=False, sheet_name="分析结论")
        
        print(f"Excel报表已生成: {report_file}")
        return report_file
    except Exception as e:
        print(f"生成分析报告时发生错误: {e}")
        return None

# 设置每日调度任务，在交易日每天9:35运行
schedule.every().day.at("09:35").do(run_daily_analysis)

# 启动用户交互（简单的命令行模式）
def main():
    print("A股智能分析系统已启动。输入'report'生成报告，输入'exit'退出。")
    try:
        while True:
            schedule.run_pending()  # 检查定时任务
            user_query = input("请输入你的问题(report/exit): ")
            
            if user_query.strip().lower() == "exit":
                print("退出智能分析系统。")
                break
                
            elif user_query.strip().lower() == "report":
                print("正在生成分析报告...")
                report_file = run_daily_analysis()
                if report_file:
                    print(f"报告已生成: {report_file}")
                    
            else:
                # 将用户问题交给代理处理，获取答案
                try:
                    answer = agent.run(user_query)
                    print("答复:", answer)
                except Exception as e:
                    print(f"处理问题时出错: {e}")
                    
    except KeyboardInterrupt:
        print("用户终止了程序。")
    finally:
        # 确保关闭MCP客户端连接
        asyncio.get_event_loop().run_until_complete(client.__aexit__(None, None, None))

if __name__ == "__main__":
    main()
