#!/usr/bin/env python3
"""
升级版策略 - 适度放宽版 (Tushare版本)
321日均线：股价在321日线上方 OR 距321日线不超过-3%
135日均量线：作为评分项而非硬过滤
景气行业：保留硬过滤
"""
import os
from pathlib import Path
import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import sys
import json
import warnings
warnings.filterwarnings('ignore')

DAILY_MA_SHORT = 60
DAILY_MA_LONG = 156
DAILY_MA_DEVIL = 321
WEEKLY_MA = 60
CROSS_DAYS = 20
NEAR_WEEKLY_MA_PCT = 4.0
VOLUME_MA = 135

HOT_SECTORS = {
    '半导体', '电子', '芯片', '集成电路', '封测', '光模块', 'PCB',
    '有色金属', '贵金属', '铜', '铝', '锂', '钴', '镍', '稀土', '黄金',
    '电力设备', '光伏', '风电', '锂电', '电池', '储能', '充电桩', '新能源',
    '机械设备', '机器人', '自动化', '工程机械', '刀具',
    '化工', '化学纤维', '化学原料', '化学制品', '氟化工', '磷化工',
    '军工', '国防', '航空航天', '地面兵装', '船舶',
    '人工智能', '算力', '大模型', 'AI', 'CPO', '通信设备',
    '医药', '创新药', '食品饮料', '消费',
    '电力', '公用事业', '港口', '高速公路',
    '玻纤', '光纤', '培育钻石', '超硬材料',
}

TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN', '')
pro = None

def init_tushare():
    global pro
    if not TUSHARE_TOKEN:
        print("警告：未设置 TUSHARE_TOKEN 环境变量")
        return False
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    return pro is not None

def get_stock_list():
    df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,industry,list_date')
    stocks = []
    for _, row in df.iterrows():
        code = row['ts_code']
        name = row['name']
        # 只保留 00、30、60 开头
        if not (code.startswith('60') or code.startswith('00') or code.startswith('30')):
            continue
        if 'ST' in name or 'st' in name or '退' in name:
            continue
        stocks.append({'code': code, 'name': name})
    print(f"获取股票列表成功（共{len(stocks)}只）")
    return stocks

def get_industry(code):
    try:
        df = pro.stock_basic(ts_code=code, fields='ts_code,industry')
        if df is not None and len(df) > 0:
            industry = df.iloc[0].get('industry', '')
            return industry, ''
    except Exception as e:
        pass
    return '', ''

def is_hot_industry(industry, industry_detail, name=''):
    check_str = (industry + industry_detail + name).upper()
    for sector in HOT_SECTORS:
        if sector in check_str or sector.upper() in check_str:
            return True, sector
    return False, ''

def process_stock(code, name):
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=600)).strftime('%Y%m%d')
    
    try:
        df = pro.daily(ts_code=code, start_date=start_date, end_date=end_date, adj='qfq')
        time.sleep(0.3)
    except Exception as e:
        return None
    
    if df is None or len(df) < DAILY_MA_DEVIL + 20:
        return None
    
    df = df.sort_values('trade_date')
    
    closes = df['close'].values
    volumes = df['vol'].values
    
    if len(closes) < DAILY_MA_DEVIL + 10:
        return None
    
    if len(volumes) > 0 and np.sum(volumes[-20:] == 0) > 10:
        return None
    
    ma60 = pd.Series(closes).rolling(DAILY_MA_SHORT).mean().values
    ma156 = pd.Series(closes).rolling(DAILY_MA_LONG).mean().values
    ma321 = pd.Series(closes).rolling(DAILY_MA_DEVIL).mean().values
    vol_ma135 = pd.Series(volumes).rolling(VOLUME_MA).mean().values
    
    above_321 = True
    price_vs_321 = None
    if not np.isnan(ma321[-1]) and ma321[-1] > 0:
        price_vs_321 = (closes[-1] - ma321[-1]) / ma321[-1] * 100
        if price_vs_321 < -5:
            return None
        if price_vs_321 < 0:
            above_321 = False
    
    cross_found = False
    days_ago = None
    
    for i in range(len(closes)-1, max(len(closes)-CROSS_DAYS-1, DAILY_MA_LONG), -1):
        if i < 1:
            break
        if np.isnan(ma60[i-1]) or np.isnan(ma156[i-1]) or np.isnan(ma60[i]) or np.isnan(ma156[i]):
            continue
        if ma60[i-1] >= ma156[i-1] and ma60[i] < ma156[i]:
            cross_found = True
            days_ago = len(closes) - 1 - i
            break
    
    if not cross_found and not np.isnan(ma60[-1]) and not np.isnan(ma156[-1]) and ma156[-1] > 0:
        diff_pct = (ma60[-1] - ma156[-1]) / ma156[-1] * 100
        if -2.0 <= diff_pct <= 0:
            for j in range(2, min(15, len(closes) - DAILY_MA_LONG)):
                idx = -(j+1)
                if not np.isnan(ma60[idx]) and not np.isnan(ma156[idx]):
                    if ma60[idx] >= ma156[idx]:
                        cross_found = True
                        days_ago = j
                        break
    
    if not cross_found:
        return None
    
    start_date_w = (datetime.now() - timedelta(days=1200)).strftime('%Y%m%d')
    try:
        df_weekly = pro.weekly(ts_code=code, start_date=start_date_w, end_date=end_date, adj='qfq')
        time.sleep(0.3)
    except:
        return None
    
    if df_weekly is None or len(df_weekly) < WEEKLY_MA + 5:
        return None
    
    df_weekly = df_weekly.sort_values('trade_date')
    w_closes = df_weekly['close'].values
    
    if len(w_closes) < WEEKLY_MA + 5:
        return None
    
    w_ma60 = pd.Series(w_closes).rolling(WEEKLY_MA).mean().values
    current_price = w_closes[-1]
    current_ma = w_ma60[-1]
    
    if np.isnan(current_ma) or current_ma == 0:
        return None
    
    deviation_pct = (current_price - current_ma) / current_ma * 100
    if abs(deviation_pct) > NEAR_WEEKLY_MA_PCT:
        return None
    
    vol_ok = False
    if not np.isnan(vol_ma135[-1]) and vol_ma135[-1] > 0:
        for k in range(min(3, len(volumes))):
            if not np.isnan(vol_ma135[-(k+1)]) and vol_ma135[-(k+1)] > 0:
                if volumes[-(k+1)] >= vol_ma135[-(k+1)]:
                    vol_ok = True
                    break
    
    lizhuangliang = False
    if len(volumes) >= 50:
        vol_50max = np.max(volumes[-50:])
        for k in range(1, min(20, len(volumes)-1)):
            idx = -k
            if abs(idx) <= len(closes) and abs(idx)+1 <= len(closes):
                if volumes[idx] >= vol_50max and closes[idx] > closes[idx+1]:
                    held = True
                    for m in range(1, min(4, abs(idx))):
                        if abs(idx-m) < len(closes):
                            if closes[idx-m] < closes[idx]:
                                held = False
                                break
                    if held:
                        lizhuangliang = True
                        break
    
    luoxuanjiang = False
    for k in range(1, min(8, len(closes)-1)):
        if k+1 < len(closes):
            day_drop = (closes[-(k+1)] - closes[-k]) / closes[-(k+1)] * 100
            if day_drop < -3:
                if k > 1 and -(k-1) >= -len(closes):
                    rebound = (closes[-(k-1)] - closes[-k]) / closes[-k] * 100
                    if rebound > 1.5:
                        luoxuanjiang = True
                        break
    
    score = 0
    tags = []
    
    score += 2
    tags.append("均线买点")
    
    if above_321:
        score += 2
        tags.append("321日线上")
    else:
        score += 0.5
        tags.append("321日线附近")
    
    if vol_ok:
        score += 2
        tags.append("量能确认")
    else:
        tags.append("量能未确认")
    
    if lizhuangliang:
        score += 3
        tags.append("立桩量")
    
    if luoxuanjiang:
        score += 2
        tags.append("螺旋桨")
    
    if abs(deviation_pct) <= 1:
        score += 1
        tags.append("精准踩线")
    
    return {
        'code': code, 'name': name,
        'current_price': closes[-1],
        'daily_ma60': round(ma60[-1], 2) if not np.isnan(ma60[-1]) else None,
        'daily_ma156': round(ma156[-1], 2) if not np.isnan(ma156[-1]) else None,
        'daily_ma321': round(ma321[-1], 2) if not np.isnan(ma321[-1]) else None,
        'price_vs_321': round(price_vs_321, 2) if price_vs_321 is not None else None,
        'above_321': above_321,
        'days_ago': days_ago,
        'weekly_ma60': round(current_ma, 2),
        'deviation_pct': round(deviation_pct, 2),
        'vol_ok': vol_ok,
        'lizhuangliang': lizhuangliang,
        'luoxuanjiang': luoxuanjiang,
        'score': score,
        'tags': '|'.join(tags),
    }

def get_fundamentals(code):
    result = {'roe': None, 'netProfit': None, 'gpMargin': None}
    try:
        df = pro.fina_indicator(ts_code=code, start_date='20250101')
        time.sleep(0.3)
        if df is not None and len(df) > 0:
            row = df.iloc[0]
            result['roe'] = row.get('roe')
            result['gpMargin'] = row.get('grossprofit_margin')
    except:
        pass
    
    if result['roe'] is None:
        try:
            df = pro.income(ts_code=code, start_date='20250101', fields='ts_code,total_revenue,gross_profit,net_profit')
            time.sleep(0.3)
            if df is not None and len(df) > 0:
                row = df.iloc[0]
                total_revenue = row.get('total_revenue', 0)
                gross_profit = row.get('gross_profit', 0)
                net_profit = row.get('net_profit', 0)
                if total_revenue and total_revenue > 0:
                    result['gpMargin'] = gross_profit / total_revenue
                result['netProfit'] = net_profit
        except:
            pass
    
    return result

def save_results(result, filename='data/strategy1.json'):
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'结果已保存到 {filename}')

def run_picker(max_results=5, progress_callback=None):
    result = {
        'success': False,
        'stocks': [],
        'message': ''
    }
    
    try:
        if not init_tushare():
            result['message'] = 'Tushare初始化失败'
            if progress_callback:
                progress_callback({'status': 'error', 'message': 'Tushare初始化失败'})
            return result
        
        if progress_callback:
            progress_callback({'status': 'loading', 'message': '获取股票列表...'})
        
        stock_list = get_stock_list()
        total = len(stock_list)
        if total == 0:
            result['message'] = '获取股票列表失败'
            if progress_callback:
                progress_callback({'status': 'error', 'message': '获取股票列表失败'})
            return result
        
        results = []
        checked = 0
        
        for i, stock in enumerate(stock_list):
            checked += 1
            code = stock['code']
            name = stock['name']
            
            if progress_callback and checked % max(1, total // 100) == 0:
                progress = checked / total * 100
                progress_callback({
                    'status': 'processing',
                    'message': f'正在分析股票... {checked}/{total}',
                    'progress': round(progress, 1),
                    'checked': checked,
                    'total': total,
                    'found': len(results)
                })
            
            try:
                tech = process_stock(code, name)
                if tech is None:
                    continue
                
                industry, industry_detail = get_industry(code)
                is_hot, matched = is_hot_industry(industry, industry_detail, name)
                if not is_hot:
                    continue
                
                fund = get_fundamentals(code)
                net_profit = fund.get('netProfit')
                roe = fund.get('roe')
                
                if net_profit and net_profit < 0:
                    continue
                if roe is not None and roe < 0:
                    continue
                
                if roe and roe * 100 > 10:
                    tech['score'] += 1
                elif roe and roe * 100 > 5:
                    tech['score'] += 0.5
                if fund.get('gpMargin') and fund['gpMargin'] * 100 > 30:
                    tech['score'] += 0.5
                
                stock_item = {
                    '代码': code,
                    '名称': name,
                    '得分': round(tech['score'], 1),
                    '行业': industry,
                    '景气标签': matched,
                    '立桩量': tech['lizhuangliang'],
                    '螺旋桨': tech['luoxuanjiang'],
                    '量能确认': tech['vol_ok'],
                    '最新价': tech['current_price'],
                    'MA321': tech['daily_ma321'],
                    '高于321线%': tech['price_vs_321'],
                    '死叉天数': tech['days_ago'],
                    '偏离60周线%': tech['deviation_pct'],
                    'ROE%': round(roe * 100, 2) if roe else None,
                    '毛利率%': round(fund.get('gpMargin', 0) * 100, 2) if fund.get('gpMargin') else None,
                    '净利润亿': round(net_profit / 1e8, 2) if net_profit else None,
                    '标签': tech['tags'],
                }
                results.append(stock_item)
                
                if progress_callback:
                    progress_callback({
                        'status': 'processing',
                        'message': f'正在分析股票... {checked}/{total}',
                        'progress': round(checked / total * 100, 1),
                        'checked': checked,
                        'total': total,
                        'found': len(results)
                    })
                
                if len(results) >= max_results:
                    break
                time.sleep(0.5)
            except Exception as e:
                pass
            
            time.sleep(0.05)
        
        results.sort(key=lambda x: x['得分'], reverse=True)
        result['stocks'] = results[:max_results]
        result['success'] = True
        result['message'] = f'检查{checked}只股票，找到{len(results)}只符合条件的股票'
        
        if progress_callback:
            progress_callback({
                'status': 'completed',
                'message': result['message'],
                'progress': 100,
                'checked': checked,
                'total': total,
                'found': len(results),
                'result': result
            })
    
    except Exception as e:
        result['message'] = f'执行出错: {str(e)}'
        if progress_callback:
            progress_callback({'status': 'error', 'message': result['message']})
    
    return result

if __name__ == '__main__':
    init_tushare()
    result = run_picker(max_results=10)
    save_results(result, 'data/strategy1.json')
    print(result['message'])