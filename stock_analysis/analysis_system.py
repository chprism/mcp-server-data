# analysis_system.py
import os
import asyncio
from langchain.llms.base import LLM
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
import schedule
import time
import pandas as pd
from dotenv import load_dotenv
import requests
from typing import Optional, List, Dict, Any
load_dotenv()

# 配置 DeepSeek API Key 等参数 (假设DeepSeek需要api_key和模型名称)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")  # 从环境变量获取DeepSeek密钥
DEEPSEEK_MODEL = "DeepSeek-V3"

# 初始化 DeepSeek 大模型客户端
llm: LLM = None
if DEEPSEEK_API_KEY:
    llm = ChatDeepSeek(api_key=DEEPSEEK_API_KEY, model=DEEPSEEK_MODEL)  # 创建DeepSeek聊天模型实例
else:
    # 如果没有DeepSeek密钥，则使用一个占位的简单LLM或抛出警告
    from langchain.llms import OpenAI  # 备用使用OpenAI或其他模型 (需有效的Key)
    llm = OpenAI(temperature=0)  # 注意：需设置OPENAI_API_KEY环境变量
    print("警告：未提供DeepSeek API Key，改用OpenAI示例模型。")

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

# 创建基于ReAct模式的智能代理
agent = create_react_agent(llm, tools)

# 定义每日分析报告生成函数
def run_daily_analysis():
    """每日自动运行的分析任务：获取数据并生成Excel报告。"""
    print("执行每日分析任务...")
    # 1. 获取当日市场整体资金流入情况和热点股票
    top_inflows = agent.run("请获取今日主力资金流入最多的5只股票，并列出它们的净流入额。")
    # 2. 获取关注股票列表的基本面与资金数据（示例固定几个股票）
    focus_stocks = ["600000.SH", "000001.SZ"]  # 示例股票代码列表（浦发银行，上证指数等）
    fundamentals_list = []
    flows_list = []
    for code in focus_stocks:
        # 调用工具获取数据
        fund_data = client.invoke_tool("get_fundamentals", {"stock_code": code})
        flow_data = client.invoke_tool("get_capital_flow", {"stock_code": code})
        fundamentals_list.append(fund_data)
        flows_list.append(flow_data)
    # 3. 获取市场新闻摘要
    news_summary = agent.run("请获取几条今天的重要财经新闻。")
    # 4. 综合以上数据生成分析结论（这里简化为字符串拼接或占位）
    analysis_text = (
        "【市场综述】今日两市主力资金净流入排名前列的股票有: {}\n"
        "【基本面】关注股票基本面摘要: {}\n"
        "【资金流】关注股票资金流摘要: {}\n"
        "【新闻影响】今日新闻摘要: {}\n"
        "【模型分析】综合来看，市场情绪{}."
    ).format(top_inflows, fundamentals_list, flows_list, news_summary, "较为积极" if "净流入" in str(top_inflows) else "需要观望")
    # （实际应用中，上述分析_text应由DeepSeek大模型根据数据生成，这里只是示例拼接）

    # 5. 生成Excel报表
    today = time.strftime("%Y%m%d")
    report_file = f"A股智能分析报告_{today}.xlsx"
    writer = pd.ExcelWriter(report_file, engine='openpyxl')
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
    analysis_df = pd.DataFrame({"分析报告": [analysis_text]})
    analysis_df.to_excel(writer, index=False, sheet_name="分析结论")
    writer.save()
    print(f"Excel报表已生成: {report_file}")

# 设置每日调度任务，在交易日每天9:35运行。这里为简化，每分钟运行一次检查（实际可判断日期）
schedule.every().day.at("09:35").do(run_daily_analysis)

# 启动用户交互（简单的命令行模式）
try:
    while True:
        schedule.run_pending()  # 检查定时任务
        user_query = input("请输入你的问题(或输入exit退出): ")
        if user_query.strip().lower() in ("exit", "quit"):
            print("退出智能分析系统。")
            break
        # 将用户问题交给代理处理，获取答案
        answer = agent.run(user_query)
        print("答复:", answer)
except KeyboardInterrupt:
    print("用户终止了程序。")
finally:
    # 确保关闭MCP客户端连接
    asyncio.get_event_loop().run_until_complete(client.__aexit__(None, None, None))
