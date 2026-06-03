#!/usr/bin/env python3
"""
升级版策略 - 适度放宽版
321日均线：股价在321日线上方 OR 距321日线不超过-3%（接近牛熊线也有反弹机会）
135日均量线：作为评分项而非硬过滤（有量能加分，无量能不扣分但不排除）
景气行业：保留硬过滤
"""
import os
from pathlib import Path
import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import sys
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

def login_bs():
    lg = bs.login()
    return lg.error_code == '0'

def get_stock_list():
    for offset in range(30):
        day = (datetime.now() - timedelta(days=offset)).strftime('%Y-%m-%d')
        rs = bs.query_all_stock(day=day)
        stocks = []
        while (rs.error_code == '0') and rs.next():
            row = rs.get_row_data()
            code = row[0]
            name = row[2] if len(row) >= 3 else row[1]
            if not (code.startswith('sh.6') or code.startswith('sz.0') or code.startswith('sz.3')):
                continue
            if 'ST' in name or 'st' in name or '退' in name:
                continue
            stocks.append({'code': code, 'name': name})
        if len(stocks) > 50:
            print(f"使用 {day} 的股票列表（共{len(stocks)}只）")
            return stocks
        elif len(stocks) > 0:
            print(f"{day} 只找到 {len(stocks)} 只股票，继续尝试...")
    print("未找到足够的股票数据")
    return []

def get_industry(code):
    rs = bs.query_stock_industry(code=code)
    data = []
    while (rs.error_code == '0') and rs.next():
        data.append(rs.get_row_data())
    if data:
        row = data[0]
        return row[3] if len(row) > 3 else '', row[-1] if len(row) > 4 else ''
    return '', ''

def is_hot_industry(industry, industry_detail, name=''):
    check_str = (industry + industry_detail + name).upper()
    for sector in HOT_SECTORS:
        if sector in check_str or sector.upper() in check_str:
            return True, sector
    return False, ''

def process_stock(code, name):
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=600)).strftime('%Y-%m-%d')
    
    rs = bs.query_history_k_data_plus(
        code, "date,close,volume",
        start_date=start_date, end_date=end_date,
        frequency="d", adjustflag="2"
    )
    daily_data = []
    while (rs.error_code == '0') and rs.next():
        daily_data.append(rs.get_row_data())
    
    if len(daily_data) < DAILY_MA_DEVIL + 20:
        return None
    
    closes = np.array([float(d[1]) for d in daily_data if d[1]])
    volumes = np.array([float(d[2]) for d in daily_data if d[2]])
    
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
    
    start_date_w = (datetime.now() - timedelta(days=1200)).strftime('%Y-%m-%d')
    rs = bs.query_history_k_data_plus(
        code, "date,close",
        start_date=start_date_w, end_date=end_date,
        frequency="w", adjustflag="2"
    )
    weekly_data = []
    while (rs.error_code == '0') and rs.next():
        weekly_data.append(rs.get_row_data())
    
    if len(weekly_data) < WEEKLY_MA + 5:
        return None
    
    w_closes = np.array([float(d[1]) for d in weekly_data if d[1]])
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
        tags.append("321日线上✓")
    else:
        score += 0.5
        tags.append("321日线附近⚠")
    
    if vol_ok:
        score += 2
        tags.append("量能确认✓")
    else:
        tags.append("量能未确认")
    
    if lizhuangliang:
        score += 3
        tags.append("🔥立桩量")
    
    if luoxuanjiang:
        score += 2
        tags.append("🌀螺旋桨")
    
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
    for y, q in [(2025, 4), (2025, 3)]:
        rs = bs.query_profit_data(code=code, year=y, quarter=q)
        data = []
        while (rs.error_code == '0') and rs.next():
            data.append(rs.get_row_data())
        if data:
            row = data[0]
            try:
                result['roe'] = float(row[3]) if row[3] else None
                result['gpMargin'] = float(row[5]) if row[5] else None
                result['netProfit'] = float(row[6]) if row[6] else None
            except:
                pass
            break
    return result

def main():
    if not login_bs():
        print("登录失败")
        return
    
    stock_list = get_stock_list()
    total = len(stock_list)
    print(f"共 {total} 只 | 策略v6：321日线±5%过滤 + 135日均量线评分 + 立桩量/螺旋桨加分")
    print("=" * 90)
    
    results = []
    checked = 0
    
    for i, stock in enumerate(stock_list):
        checked += 1
        code = stock['code']
        name = stock['name']
        
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
            
            result = {
                '代码': code, '名称': name, '行业': industry,
                '景气标签': matched, '得分': tech['score'],
                '最新价': tech['current_price'],
                'MA321': tech['daily_ma321'],
                '高于321线%': tech['price_vs_321'],
                '死叉天数': tech['days_ago'],
                '偏离60周线%': tech['deviation_pct'],
                '量能确认': '✓' if tech['vol_ok'] else '⚠',
                '立桩量': '🔥' if tech['lizhuangliang'] else '-',
                '螺旋桨': '🌀' if tech['luoxuanjiang'] else '-',
                'ROE%': round(roe * 100, 2) if roe else None,
                '毛利率%': round(fund.get('gpMargin', 0) * 100, 2) if fund.get('gpMargin') else None,
                '净利润亿': round(net_profit / 1e8, 2) if net_profit else None,
                '标签': tech['tags'],
            }
            results.append(result)
            
            m = ''
            if tech['lizhuangliang']: m += '🔥'
            if tech['luoxuanjiang']: m += '🌀'
            if tech['vol_ok']: m += '✓'
            print(f"  ✓ [{len(results)}] {code} {name} | {matched} | {tech['score']:.1f}分 | 死叉{tech['days_ago']}天 | 321线{tech['price_vs_321']}% | {m}")
            sys.stdout.flush()
            
            if len(results) >= 20:
                break
            time.sleep(0.2)
        except:
            pass
        
        if checked % 300 == 0:
            print(f"进度: {checked}/{total} ({checked/total*100:.1f}%) | 找到: {len(results)}")
            sys.stdout.flush()
        time.sleep(0.05)
    
    print(f"\n完成！检查{checked}只，找到{len(results)}只")
    
    if results:
        df = pd.DataFrame(results)
        df = df.sort_values('得分', ascending=False)
        
        print("\n" + "=" * 100)
        print(df[['代码','名称','景气标签','得分','量能确认','立桩量','螺旋桨','高于321线%','偏离60周线%','ROE%']].to_string(index=False))
        
        top5 = df.head(5)
        print("\n🏆 今日推荐5只（升级版策略）：\n")
        for i, (_, row) in enumerate(top5.iterrows(), 1):
            print(f"📌 第{i}只：{row['代码']} {row['名称']}")
            print(f"   赛道: {row['景气标签']} | 得分: {row['得分']:.1f}")
            print(f"   死叉: {row['死叉天数']}天 | 偏离60周线: {row['偏离60周线%']}% | 高于321线: {row['高于321线%']}%")
            print(f"   量能: {row['量能确认']} | 立桩量: {row['立桩量']} | 螺旋桨: {row['螺旋桨']}")
            print(f"   ROE: {row['ROE%']}% | 毛利: {row['毛利率%']}% | 净利: {row['净利润亿']}亿")
            print(f"   标签: {row['标签']}")
            print()
        
        top5.to_csv('stock_v6_top5.csv', index=False, encoding='utf-8-sig')
        df.to_csv('/sandbox/workspace/stock_v6_all.csv', index=False, encoding='utf-8-sig')
    
    bs.logout()

def run_picker(max_results=5, progress_callback=None):
    result = {
        'success': False,
        'stocks': [],
        'message': ''
    }
    
    try:
        if not login_bs():
            result['message'] = '登录失败'
            if progress_callback:
                progress_callback({'status': 'error', 'message': '登录失败'})
            return result
        
        if progress_callback:
            progress_callback({'status': 'loading', 'message': '获取股票列表...'})
        
        stock_list = get_stock_list()
        total = len(stock_list)
        if total == 0:
            result['message'] = '获取股票列表失败'
            bs.logout()
            if progress_callback:
                progress_callback({'status': 'error', 'message': '获取股票列表失败'})
            return result
        
        results = []
        checked = 0
        
        for i, stock in enumerate(stock_list):
            checked += 1
            code = stock['code']
            name = stock['name']
            
            if progress_callback and checked % 10 == 0:
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
                time.sleep(0.2)
            except:
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
        
        bs.logout()
    except Exception as e:
        result['message'] = f'执行出错: {str(e)}'
        if progress_callback:
            progress_callback({'status': 'error', 'message': result['message']})
    
    return result

if __name__ == '__main__':
    main()
