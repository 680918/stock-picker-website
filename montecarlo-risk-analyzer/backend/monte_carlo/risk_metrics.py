import numpy as np

def calculate_max_drawdown(portfolio_values):
    """计算最大回撤"""
    max_values = np.maximum.accumulate(portfolio_values, axis=1)
    drawdowns = 1 - portfolio_values / max_values
    max_drawdowns = np.max(drawdowns, axis=1)
    return max_drawdowns

def calculate_var(returns, confidence_level=0.95):
    """计算 VaR (Value at Risk)"""
    return -np.percentile(returns, (1 - confidence_level) * 100)

def calculate_cvar(returns, confidence_level=0.95):
    """计算 CVaR (Conditional VaR)"""
    var = calculate_var(returns, confidence_level)
    tail_returns = returns[returns <= -var]
    return -np.mean(tail_returns)

def calculate_metrics(portfolio_values, initial_capital):
    """计算所有风险指标"""
    final_values = portfolio_values[:, -1]
    total_returns = (final_values - initial_capital) / initial_capital
    
    # 计算日收益率
    daily_returns = np.diff(portfolio_values, axis=1) / portfolio_values[:, :-1]
    
    # 最大回撤
    max_drawdowns = calculate_max_drawdown(portfolio_values)
    
    # VaR 和 CVaR
    var_95 = float(calculate_var(total_returns, 0.95))
    cvar_95 = float(calculate_cvar(total_returns, 0.95))
    
    # 统计指标
    metrics = {
        'expected_return': float(np.mean(total_returns)),
        'return_std': float(np.std(total_returns)),
        'return_min': float(np.min(total_returns)),
        'return_max': float(np.max(total_returns)),
        'return_median': float(np.median(total_returns)),
        'max_drawdown_mean': float(np.mean(max_drawdowns)),
        'max_drawdown_95': float(np.percentile(max_drawdowns, 95)),
        'var_95': var_95,
        'cvar_95': cvar_95,
        'sharpe_ratio': float(np.mean(total_returns) / np.std(total_returns)) if np.std(total_returns) > 0 else 0,
        'probability_of_profit': float(np.mean(total_returns > 0)),
        'probability_of_loss': float(np.mean(total_returns < 0))
    }
    
    return metrics, total_returns, max_drawdowns

def get_risk_rating(metrics):
    """根据指标计算风险评级"""
    score = 0
    
    # 收益稳定性 (30分)
    if metrics['return_std'] < 0.1:
        score += 30
    elif metrics['return_std'] < 0.2:
        score += 20
    else:
        score += 10
    
    # 最大回撤 (30分)
    if metrics['max_drawdown_95'] < 0.15:
        score += 30
    elif metrics['max_drawdown_95'] < 0.3:
        score += 20
    else:
        score += 10
    
    # VaR (20分)
    if metrics['var_95'] < 0.1:
        score += 20
    elif metrics['var_95'] < 0.2:
        score += 15
    else:
        score += 5
    
    # 夏普比率 (20分)
    if metrics['sharpe_ratio'] > 1:
        score += 20
    elif metrics['sharpe_ratio'] > 0.5:
        score += 15
    else:
        score += 5
    
    # 评级
    if score >= 80:
        return {'rating': 'A', 'color': '#22c55e', 'label': '低风险'}
    elif score >= 60:
        return {'rating': 'B', 'color': '#eab308', 'label': '中等风险'}
    elif score >= 40:
        return {'rating': 'C', 'color': '#f97316', 'label': '较高风险'}
    else:
        return {'rating': 'D', 'color': '#ef4444', 'label': '高风险'}