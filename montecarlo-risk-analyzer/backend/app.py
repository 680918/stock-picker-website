from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import tushare as ts
import os

from monte_carlo.data_loader import get_stock_data, calculate_stock_stats
from monte_carlo.simulator import run_portfolio_simulation
from monte_carlo.risk_metrics import calculate_metrics, get_risk_rating

app = Flask(__name__)
CORS(app)

def convert_to_serializable(obj):
    """将 numpy 类型转换为可 JSON 序列化的类型"""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    return obj

@app.route('/api/stocks', methods=['GET'])
def get_stock_info():
    """获取股票基本信息"""
    ts_code = request.args.get('code')
    
    if not ts_code:
        return jsonify({'success': False, 'message': '请提供股票代码'})
    
    try:
        df = get_stock_data(ts_code)
        if df is None or df.empty:
            return jsonify({'success': False, 'message': '获取股票数据失败'})
        
        stats = calculate_stock_stats(df)
        
        return jsonify({
            'success': True,
            'data': {
                'ts_code': ts_code,
                'latest_price': float(df['close'].iloc[-1]),
                'stats': convert_to_serializable(stats)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/montecarlo/run', methods=['POST'])
def run_montecarlo():
    """执行蒙特卡罗模拟"""
    try:
        data = request.json
        
        stock_codes = data.get('stock_codes', [])
        weights = data.get('weights', [])
        initial_capital = data.get('initial_capital', 100000)
        simulation_days = data.get('simulation_days', 252)
        num_simulations = data.get('num_simulations', 1000)
        
        if not stock_codes:
            return jsonify({'success': False, 'message': '请提供股票代码'})
        
        if not weights or len(weights) != len(stock_codes):
            weights = [1/len(stock_codes)] * len(stock_codes)
        
        stock_data = []
        for code in stock_codes:
            df = get_stock_data(code)
            if df is None or df.empty:
                return jsonify({'success': False, 'message': f'获取股票 {code} 数据失败'})
            
            stats = calculate_stock_stats(df)
            # 将 returns 作为 numpy 数组传递，避免精度丢失
            returns = df['return'].dropna().values
            stock_data.append({
                'code': code,
                'returns': returns,
                'annual_return': stats['annualized_return'],
                'annual_volatility': stats['annualized_volatility'],
                'latest_price': float(df['close'].iloc[-1])
            })
        
        portfolio_values = run_portfolio_simulation(
            stock_data,
            weights,
            initial_capital,
            simulation_days,
            num_simulations
        )
        
        metrics, total_returns, max_drawdowns = calculate_metrics(portfolio_values, initial_capital)
        
        risk_rating = get_risk_rating(metrics)
        
        sample_size = min(100, num_simulations)
        sample_indices = np.random.choice(num_simulations, sample_size, replace=False)
        sample_paths = portfolio_values[sample_indices, :].tolist()
        
        result = {
            'success': True,
            'parameters': {
                'stock_codes': stock_codes,
                'weights': weights,
                'initial_capital': initial_capital,
                'simulation_days': simulation_days,
                'num_simulations': num_simulations
            },
            'metrics': convert_to_serializable(metrics),
            'risk_rating': convert_to_serializable(risk_rating),
            'return_distribution': convert_to_serializable(total_returns),
            'drawdown_distribution': convert_to_serializable(max_drawdowns),
            'sample_paths': sample_paths,
            'stock_info': [
                {
                    'code': sd['code'],
                    'annual_return': float(sd['annual_return']),
                    'annual_volatility': float(sd['annual_volatility']),
                    'latest_price': float(sd['latest_price'])
                }
                for sd in stock_data
            ]
        }
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/montecarlo/quick', methods=['POST'])
def quick_analysis():
    """快速分析单只股票"""
    try:
        data = request.json
        ts_code = data.get('ts_code')
        
        if not ts_code:
            return jsonify({'success': False, 'message': '请提供股票代码'})
        
        df = get_stock_data(ts_code)
        if df is None or df.empty:
            return jsonify({'success': False, 'message': '获取股票数据失败'})
        
        stats = calculate_stock_stats(df)
        
        mu = stats['annualized_return']
        sigma = stats['annualized_volatility']
        initial_price = df['close'].iloc[-1]
        
        num_simulations = 1000
        days = 60
        
        dt = 1 / 252
        prices = np.zeros((num_simulations, days))
        prices[:, 0] = initial_price
        
        for i in range(1, days):
            dW = np.random.normal(0, np.sqrt(dt), num_simulations)
            prices[:, i] = prices[:, i-1] * np.exp((mu - 0.5 * sigma**2) * dt + sigma * dW)
        
        final_prices = prices[:, -1]
        returns = (final_prices - initial_price) / initial_price
        
        max_drawdowns = []
        for i in range(num_simulations):
            max_price = np.max(prices[i])
            drawdown = 1 - prices[i, -1] / max_price
            max_drawdowns.append(float(drawdown))
        
        result = {
            'success': True,
            'ts_code': ts_code,
            'latest_price': float(initial_price),
            'stats': convert_to_serializable(stats),
            'simulation': {
                'expected_return': float(np.mean(returns)),
                'return_std': float(np.std(returns)),
                'return_min': float(np.min(returns)),
                'return_max': float(np.max(returns)),
                'max_drawdown_mean': float(np.mean(max_drawdowns)),
                'max_drawdown_95': float(np.percentile(max_drawdowns, 95)),
                'probability_of_profit': float(np.mean(returns > 0))
            },
            'return_distribution': returns[:100].tolist()
        }
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)