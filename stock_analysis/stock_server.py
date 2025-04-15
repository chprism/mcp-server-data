# stock_server.py
from mcp.server.fastmcp import FastMCP

# 创建MCP服务器实例，命名为 "AStockData"
mcp = FastMCP("AStockData")

# 1. 获取当日资金流入最多的前N只股票
@mcp.tool()
def get_top_inflows(top_n: int = 5) -> list:
    """获取今日主力资金净流入最多的前N只股票及金额。返回列表，每项为(股票名称, 净流入额)。"""
    # **实际应用**: 调用数据源获取今日资金流入排名，例如通过Tushare的资金流向接口
    # 这里使用模拟数据
    sample_data = [
        ("贵州茅台", 5.3),
        ("平安银行", 4.1),
        ("招商证券", 3.8),
        ("宁德时代", 3.5),
        ("万科A", 2.9)
    ]
    return sample_data[:top_n]

# 2. 获取指定股票的资金流动数据
@mcp.tool()
def get_capital_flow(stock_code: str) -> dict:
    """获取指定股票今日的资金流向数据，返回字典包括净流入额、买入额、卖出额等。"""
    # **实际应用**: 查询实时资金流，如主力/散户资金净流入。这里用模拟值。
    data = {
        "stock": stock_code,
        "net_inflow": 1.2,      # 主力净流入（亿元）
        "buy_amount": 5.6,     # 主力买入额
        "sell_amount": 4.4     # 主力卖出额
    }
    return data

# 3. 获取指定股票的基本面摘要
@mcp.tool()
def get_fundamentals(stock_code: str) -> dict:
    """获取股票最新基本面数据摘要，如市值、PE、ROE等。"""
    # **实际应用**: 查询财报或行情数据，这里简化为示例数据
    data = {
        "stock": stock_code,
        "price": 25.30,        # 最新股价
        "pe_ratio": 12.5,      # 市盈率
        "roe": 15.2,           # 净资产收益率（%）
        "revenue_growth": 8.3  # 营收增长率（%）
    }
    return data

# 4. 获取指定股票的新闻摘要
@mcp.tool()
def get_news(stock_code: str) -> list:
    """获取指定股票相关的最新新闻标题列表。"""
    # **实际应用**: 调用新闻API或爬虫，这里返回模拟新闻
    sample_news = [
        f"{stock_code}: 公司发布季度业绩，利润同比增长20%",
        f"{stock_code}: 宣布与知名企业达成战略合作",
        f"{stock_code}: 所在行业迎来政策利好，市场前景看好"
    ]
    return sample_news

# 运行MCP服务（如果直接执行此脚本）
if __name__ == "__main__":
    # 启动MCP服务器并监听（使用标准IO协议，方便本地客户端调用）
    mcp.run()
