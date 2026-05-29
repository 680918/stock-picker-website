#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股热点板块自动识别系统 - 网站版
输出格式：JSON，供前端展示
"""

import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import os

# ==================== 配置 ====================
TOP_N = 5                      # 输出前N个热点板块
MIN_UP_NUMS = 3                 # 最低涨停家数阈值
DAYS_THRESHOLD = 3              # 持续上榜天数阈值
# =============================================

def get_latest_trade_date(pro):
    today = datetime.now()
    for offset in range(10):
        d = (today - timedelta(days=offset)).strftime('%Y%m%d')
        try:
            test = pro.daily(trade_date=d, limit=1)
            if not test.empty:
                return d
        except:
            continue
        time.sleep(0.1)
    raise RuntimeError("无法获取交易日数据")

def get_sector_heat(pro, trade_date):
    df = pro.limit_cpt_list(trade_date=trade_date)
    if df.empty:
        return df
    df['up_nums'] = pd.to_numeric(df['up_nums'], errors='coerce')
    df = df[df['up_nums'] >= MIN_UP_NUMS].copy()
    return df

def calculate_comprehensive_score(row):
    up_nums = float(row['up_nums']) if row['up_nums'] else 0
    pct_chg = float(row['pct_chg']) if row['pct_chg'] else 0
    days = float(row['days']) if row['days'] else 0
    cons_nums = float(row['cons_nums']) if row['cons_nums'] else 0
    
    up_score = min(up_nums / 20, 1.0) * 40
    pct_score = min(max(pct_chg / 10, 0), 1.0) * 30
    days_score = min(days / 10, 1.0) * 20
    cons_score = min(cons_nums / 10, 1.0) * 10
    
    return round(up_score + pct_score + days_score + cons_score, 2)

def main():
    ts.set_token(os.environ.get('TUSHARE_TOKEN'))
    pro = ts.pro_api()
    
    trade_date = get_latest_trade_date(pro)
    print(f"分析日期：{trade_date}")
    
    hot_df = get_sector_heat(pro, trade_date)
    
    result = {
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'trade_date': trade_date,
        'sectors': []
    }
    
    if hot_df.empty:
        result['message'] = "今日无热点板块（涨停家数不足）"
    else:
        numeric_cols = ['up_nums', 'pct_chg', 'days', 'cons_nums']
        for col in numeric_cols:
            hot_df[col] = pd.to_numeric(hot_df[col], errors='coerce')
        
        hot_df['综合评分'] = hot_df.apply(calculate_comprehensive_score, axis=1)
        hot_df = hot_df.sort_values('综合评分', ascending=False)
        
        for idx, (_, row) in enumerate(hot_df.head(TOP_N).iterrows(), 1):
            result['sectors'].append({
                'rank': idx,
                'name': str(row['name']) if pd.notna(row['name']) else '',
                'up_nums': int(row['up_nums']) if pd.notna(row['up_nums']) else 0,
                'pct_chg': round(row['pct_chg'], 2) if pd.notna(row['pct_chg']) else 0,
                'days': int(row['days']) if pd.notna(row['days']) else 0,
                'cons_nums': int(row['cons_nums']) if pd.notna(row['cons_nums']) else 0,
                'score': row['综合评分'],
                'is_hot': (row['days'] >= DAYS_THRESHOLD) if pd.notna(row['days']) else False,
                'up_stat': str(row['up_stat']) if 'up_stat' in row and pd.notna(row['up_stat']) else ''
            })
        result['message'] = f"共找到{len(hot_df)}个热点板块，显示前{TOP_N}个"
    
    os.makedirs('data', exist_ok=True)
    with open('data/hot_sectors.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"热点板块数据已保存")
    return result

if __name__ == '__main__':
    main()