# stock_server.py
from mcp.server.fastmcp import FastMCP
import akshare as ak
import pandas as pd
import time
import os
from functools import lru_cache
import requests
from datetime import datetime

# 创建MCP服务器实例，命名为 "AStockData"
mcp = FastMCP("AStockData")

@lru_cache(maxsize=128)
def get_cached_data(func, *args, **kwargs):
    """数据缓存装饰器，缓存时间为5分钟"""
    return func(*args, **kwargs)

# 1. 获取当日资金流入最多的前N只股票
@mcp.tool()
def get_top_inflows(top_n: int = 5) -> list:
    """获取今日主力资金净流入最多的前N只股票及金额。返回列表，每项为(股票名称, 净流入额)。"""
    try:
        df = get_cached_data(ak.stock_fund_flow_individual)
        
        if df is None or df.empty:
            return [("获取数据失败", 0)]
        
        df = df.sort_values(by="主力净流入-净额", ascending=False).head(top_n)
        
        result = [(row["名称"], round(row["主力净流入-净额"]/100000000, 2)) for _, row in df.iterrows()]
        return result
    except Exception as e:
        print(f"获取资金流入数据时出错: {e}")
        return [("数据获取错误", 0)]

# 2. 获取指定股票的资金流动数据
@mcp.tool()
def get_capital_flow(stock_code: str) -> dict:
    """获取指定股票今日的资金流向数据，返回字典包括净流入额、买入额、卖出额等。"""
    try:
        df = get_cached_data(ak.stock_individual_fund_flow, symbol=stock_code)
        
        if df is None or df.empty:
            return {"stock": stock_code, "error": "未找到数据"}
        
        latest_data = df.iloc[0]
        
        result = {
            "stock": stock_code,
            "net_inflow": round(latest_data["主力净流入"] / 100000000, 2),  # 转为亿元并保留两位小数
            "buy_amount": round(latest_data["主力买入"] / 100000000, 2),
            "sell_amount": round(latest_data["主力卖出"] / 100000000, 2)
        }
        return result
    except Exception as e:
        print(f"获取股票{stock_code}资金流数据时出错: {e}")
        return {"stock": stock_code, "error": str(e)}

# 3. 获取指定股票的基本面摘要
@mcp.tool()
def get_fundamentals(stock_code: str) -> dict:
    """获取股票最新基本面数据摘要，如市值、PE、ROE等。"""
    try:
        df_info = get_cached_data(ak.stock_individual_info, symbol=stock_code)
        
        if df_info is None or df_info.empty:
            return {"stock": stock_code, "error": "未找到数据"}
        
        price_data = get_cached_data(ak.stock_zh_a_spot)
        price_data = price_data[price_data['代码'] == stock_code]
        current_price = price_data['最新价'].values[0] if not price_data.empty else 0
        
        result = {
            "stock": stock_code,
            "price": current_price,
            "pe_ratio": float(df_info[df_info['item'] == '市盈率(动态)']['value'].values[0]) if '市盈率(动态)' in df_info['item'].values else 0,
            "roe": float(df_info[df_info['item'] == 'ROE(%)']['value'].values[0]) if 'ROE(%)' in df_info['item'].values else 0,
            "revenue_growth": float(df_info[df_info['item'] == '营业收入同比增长(%)']['value'].values[0]) if '营业收入同比增长(%)' in df_info['item'].values else 0
        }
        return result
    except Exception as e:
        print(f"获取股票{stock_code}基本面数据时出错: {e}")
        return {"stock": stock_code, "error": str(e)}

# 4. 获取指定股票的新闻摘要
@mcp.tool()
def get_news(stock_code: str) -> list:
    """获取指定股票相关的最新新闻标题列表。"""
    try:
        df_news = get_cached_data(ak.stock_news_em)
        
        if df_news is None or df_news.empty:
            return [f"{stock_code}: 未找到相关新闻"]
        
        stock_name = ""
        try:
            stock_info = get_cached_data(ak.stock_individual_info_em, symbol=stock_code)
            if not stock_info.empty:
                stock_name = stock_info.iloc[0]['股票简称']
        except:
            pass
        
        filtered_news = []
        if stock_name:
            for _, row in df_news.iterrows():
                if stock_name in str(row['标题']) or stock_code in str(row['标题']):
                    filtered_news.append(f"{stock_code}: {row['标题']}")
                if len(filtered_news) >= 3:  # 最多返回3条新闻
                    break
        
        if not filtered_news:
            filtered_news = [f"{stock_code}: {row['标题']}" for _, row in df_news.head(3).iterrows()]
            
        return filtered_news
    except Exception as e:
        print(f"获取股票{stock_code}新闻时出错: {e}")
        return [f"{stock_code}: 获取新闻数据出错: {str(e)}"]

# 运行MCP服务（如果直接执行此脚本）
if __name__ == "__main__":
    # 启动MCP服务器并监听（使用标准IO协议，方便本地客户端调用）
    mcp.run()
