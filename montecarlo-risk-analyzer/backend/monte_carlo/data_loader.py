import tushare as ts
import pandas as pd
import numpy as np
import os

def get_stock_data(ts_code, start_date='20200101', end_date=None):
    """获取股票历史数据"""
    token = os.environ.get('TUSHARE_TOKEN', '98cf930ca6e181e63f7e2a06e000d3bffc0e2fbda56b2fd6435da46b')
    pro = ts.pro_api(token=token)
    
    if end_date is None:
        from datetime import datetime
        end_date = datetime.now().strftime('%Y%m%d')
    
    df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date, adj='qfq')
    
    if df.empty:
        return None
    
    df = df.sort_values('trade_date')
    df['return'] = df['close'].pct_change().dropna()
    
    return df

def calculate_stock_stats(df):
    """计算股票统计特征"""
    returns = df['return'].dropna()
    
    stats = {
        'mean_return': float(returns.mean()),
        'std_return': float(returns.std()),
        'annualized_return': float(returns.mean() * 252),
        'annualized_volatility': float(returns.std() * np.sqrt(252)),
        'sharpe_ratio': float((returns.mean() * 252) / (returns.std() * np.sqrt(252))),
        'skewness': float(returns.skew()),
        'kurtosis': float(returns.kurtosis())
    }
    
    return stats