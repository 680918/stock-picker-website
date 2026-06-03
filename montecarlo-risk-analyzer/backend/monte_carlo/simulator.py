import numpy as np

def simulate_gbm(initial_price, mu, sigma, days, num_simulations):
    """
    几何布朗运动模拟
    dS/S = μdt + σdW
    """
    dt = 1 / 252
    results = np.zeros((num_simulations, days))
    results[:, 0] = initial_price
    
    for i in range(1, days):
        dW = np.random.normal(0, np.sqrt(dt), num_simulations)
        results[:, i] = results[:, i-1] * np.exp((mu - 0.5 * sigma**2) * dt + sigma * dW)
    
    return results

def run_portfolio_simulation(stock_data, weights, initial_capital, days, num_simulations):
    """运行投资组合蒙特卡罗模拟"""
    num_stocks = len(stock_data)
    portfolio_values = np.zeros((num_simulations, days))
    portfolio_values[:, 0] = initial_capital
    
    # 确保所有股票的收益率数组长度一致
    min_len = min(len(sd['returns']) for sd in stock_data)
    if min_len < 10:
        raise ValueError("历史数据不足，无法进行模拟")
    
    # 截取相同长度的收益率数据
    returns_list = [sd['returns'][:min_len] for sd in stock_data]
    returns_matrix = np.column_stack(returns_list)
    
    # 计算协方差矩阵（确保是二维方阵）
    if num_stocks == 1:
        # 单只股票，手动构造 1x1 协方差矩阵
        cov_matrix = np.array([[np.var(returns_list[0])]])
    else:
        # 多只股票，计算协方差矩阵
        cov_matrix = np.cov(returns_matrix, rowvar=False)
    
    # 确保协方差矩阵是二维的
    if cov_matrix.ndim == 0:
        cov_matrix = np.array([[cov_matrix]])
    elif cov_matrix.ndim == 1:
        cov_matrix = cov_matrix.reshape(1, -1)
    
    # 年化收益率和波动率
    annual_returns = np.array([sd['annual_return'] for sd in stock_data])
    annual_vols = np.array([sd['annual_volatility'] for sd in stock_data])
    
    dt = 1 / 252
    
    for day in range(1, days):
        # 生成多元正态随机数
        correlated_returns = np.random.multivariate_normal(
            annual_returns * dt,
            cov_matrix * dt,
            num_simulations
        )
        
        # 计算组合收益
        portfolio_returns = np.dot(correlated_returns, weights)
        
        # 更新组合价值
        portfolio_values[:, day] = portfolio_values[:, day-1] * (1 + portfolio_returns)
    
    return portfolio_values