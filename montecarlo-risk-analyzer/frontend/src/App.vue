<template>
  <div class="container">
    <div class="header">
      <h1>🎲 蒙特卡罗风险分析系统</h1>
      <p>基于历史数据的策略压力测试与风险评估</p>
    </div>
    
    <div class="card">
      <div class="card-title">📊 参数设置</div>
      <div class="input-group">
        <div class="input-item">
          <label>股票代码 (逗号分隔)</label>
          <input v-model="stockCodes" placeholder="如：000001.SZ,600036.SH" />
        </div>
        <div class="input-item">
          <label>初始资金 (元)</label>
          <input v-model.number="initialCapital" type="number" placeholder="100000" />
        </div>
        <div class="input-item">
          <label>模拟天数</label>
          <select v-model.number="simulationDays">
            <option :value="30">30 天 (1 个月)</option>
            <option :value="60">60 天 (2 个月)</option>
            <option :value="120">120 天 (4 个月)</option>
            <option :value="252">252 天 (1 年)</option>
          </select>
        </div>
        <div class="input-item">
          <label>模拟次数</label>
          <select v-model.number="numSimulations">
            <option :value="500">500 次</option>
            <option :value="1000">1000 次</option>
            <option :value="2000">2000 次</option>
          </select>
        </div>
      </div>
      <button class="btn btn-primary" @click="runSimulation" :disabled="loading">
        {{ loading ? '⏳ 计算中...' : '🚀 开始模拟' }}
      </button>
    </div>
    
    <div v-if="error" class="error-message">
      ⚠️ {{ error }}
    </div>
    
    <div v-if="loading" class="card">
      <div class="loading">
        <div class="loading-spinner"></div>
        <div>正在运行蒙特卡罗模拟...</div>
        <div style="font-size: 0.8rem; color: #999; margin-top: 10px;">
          这可能需要几秒钟时间，请耐心等待
        </div>
      </div>
    </div>
    
    <div v-if="result && !loading">
      <div class="card">
        <div class="card-title">🏆 风险评级</div>
        <div class="risk-rating">
          <div class="rating-circle" :style="{ background: result.risk_rating.color }">
            {{ result.risk_rating.rating }}
          </div>
          <div class="rating-info">
            <div class="rating-label">{{ result.risk_rating.label }}</div>
            <div class="rating-desc">基于收益波动率、最大回撤、VaR 等指标综合评估</div>
          </div>
        </div>
      </div>
      
      <div class="card">
        <div class="card-title">📈 核心指标</div>
        <div class="grid">
          <div class="metric-card">
            <div class="metric-value" :class="result.metrics.expected_return > 0 ? 'text-green' : 'text-red'">
              {{ (result.metrics.expected_return * 100).toFixed(2) }}%
            </div>
            <div class="metric-label">期望收益</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{{ (result.metrics.return_std * 100).toFixed(2) }}%</div>
            <div class="metric-label">收益波动率</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{{ (result.metrics.max_drawdown_95 * 100).toFixed(2) }}%</div>
            <div class="metric-label">最大回撤 (95%)</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{{ (result.metrics.var_95 * 100).toFixed(2) }}%</div>
            <div class="metric-label">VaR (95%)</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{{ (result.metrics.cvar_95 * 100).toFixed(2) }}%</div>
            <div class="metric-label">CVaR (95%)</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{{ result.metrics.sharpe_ratio.toFixed(2) }}</div>
            <div class="metric-label">夏普比率</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{{ (result.metrics.probability_of_profit * 100).toFixed(0) }}%</div>
            <div class="metric-label">盈利概率</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">{{ (result.metrics.probability_of_loss * 100).toFixed(0) }}%</div>
            <div class="metric-label">亏损概率</div>
          </div>
        </div>
      </div>
      
      <div class="card">
        <div class="card-title">📊 收益分布图</div>
        <div class="chart-container" ref="returnChart"></div>
      </div>
      
      <div class="card">
        <div class="card-title">📉 回撤概率分布</div>
        <div class="chart-container" ref="drawdownChart"></div>
      </div>
      
      <div class="card">
        <div class="card-title">📈 模拟路径示例</div>
        <div class="chart-container" ref="pathChart"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const stockCodes = ref('000001.SZ')
const initialCapital = ref(100000)
const simulationDays = ref(252)
const numSimulations = ref(1000)
const loading = ref(false)
const error = ref('')
const result = ref(null)

const returnChart = ref(null)
const drawdownChart = ref(null)
const pathChart = ref(null)

const runSimulation = async () => {
  loading.value = true
  error.value = ''
  result.value = null
  
  try {
    const response = await fetch('http://localhost:5001/api/montecarlo/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        stock_codes: stockCodes.value.split(',').map(s => s.trim()).filter(s => s),
        initial_capital: initialCapital.value,
        simulation_days: simulationDays.value,
        num_simulations: numSimulations.value
      })
    })
    
    const data = await response.json()
    
    if (data.success) {
      result.value = data
      console.log('后端返回的数据:', data)
      console.log('收益分布数据长度:', data.return_distribution?.length)
      console.log('回撤分布数据长度:', data.drawdown_distribution?.length)
      console.log('模拟路径数量:', data.sample_paths?.length)
      console.log('模拟天数:', data.parameters?.simulation_days)
      await nextTick()
      setTimeout(() => {
        renderCharts()
      }, 100)
    } else {
      error.value = data.message || '模拟失败'
    }
  } catch (err) {
    error.value = '网络错误，请确保后端服务已启动：' + err.message
    console.error('请求错误:', err)
  } finally {
    loading.value = false
  }
}

const renderCharts = () => {
  console.log('开始渲染图表')
  
  // 收益分布图
  if (returnChart.value) {
    console.log('渲染收益分布图')
    const chart = echarts.init(returnChart.value)
    const returns = result.value.return_distribution
    
    if (!returns || returns.length === 0) {
      console.error('收益分布数据为空')
      return
    }
    
    // 计算直方图数据
    const binCount = 50
    const min = Math.min(...returns)
    const max = Math.max(...returns)
    const binWidth = (max - min) / binCount
    const bins = new Array(binCount).fill(0)
    
    returns.forEach(r => {
      const binIndex = Math.min(Math.floor((r - min) / binWidth), binCount - 1)
      bins[binIndex]++
    })
    
    const binLabels = []
    for (let i = 0; i < binCount; i++) {
      const binCenter = min + (i + 0.5) * binWidth
      binLabels.push((binCenter * 100).toFixed(1))
    }
    
    console.log('收益分布图数据：bins 长度=', bins.length)
    
    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        name: '收益率 (%)',
        data: binLabels,
        axisLabel: {
          interval: 9,
          rotate: 45
        }
      },
      yAxis: {
        type: 'value',
        name: '频数'
      },
      series: [{
        name: '收益分布',
        type: 'bar',
        data: bins,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#667eea' },
            { offset: 1, color: '#764ba2' }
          ])
        }
      }]
    }
    
    chart.setOption(option)
    window.addEventListener('resize', () => chart.resize())
    console.log('收益分布图渲染完成')
  } else {
    console.error('returnChart ref 为空')
  }
  
  // 回撤分布图
  if (drawdownChart.value) {
    console.log('渲染回撤分布图')
    const chart = echarts.init(drawdownChart.value)
    const drawdowns = result.value.drawdown_distribution
    
    if (!drawdowns || drawdowns.length === 0) {
      console.error('回撤分布数据为空')
      return
    }
    
    // 计算直方图数据
    const binCount = 50
    const min = Math.min(...drawdowns)
    const max = Math.max(...drawdowns)
    const binWidth = (max - min) / binCount
    const bins = new Array(binCount).fill(0)
    
    drawdowns.forEach(d => {
      const binIndex = Math.min(Math.floor((d - min) / binWidth), binCount - 1)
      bins[binIndex]++
    })
    
    const binLabels = []
    for (let i = 0; i < binCount; i++) {
      const binCenter = min + (i + 0.5) * binWidth
      binLabels.push((binCenter * 100).toFixed(1))
    }
    
    console.log('回撤分布图数据：bins 长度=', bins.length)
    
    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        name: '最大回撤 (%)',
        data: binLabels,
        axisLabel: {
          interval: 9,
          rotate: 45
        }
      },
      yAxis: {
        type: 'value',
        name: '频数'
      },
      series: [{
        name: '回撤分布',
        type: 'bar',
        data: bins,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#f97316' },
            { offset: 1, color: '#ef4444' }
          ])
        }
      }]
    }
    
    chart.setOption(option)
    window.addEventListener('resize', () => chart.resize())
    console.log('回撤分布图渲染完成')
  } else {
    console.error('drawdownChart ref 为空')
  }
  
  // 模拟路径图
  if (pathChart.value) {
    console.log('渲染模拟路径图')
    const chart = echarts.init(pathChart.value)
    const paths = result.value.sample_paths
    const days = result.value.parameters.simulation_days
    
    if (!paths || paths.length === 0) {
      console.error('模拟路径数据为空')
      return
    }
    
    console.log('模拟路径数据：paths 长度=', paths.length, 'days=', days)
    
    const series = paths.map((path, index) => ({
      name: `路径 ${index + 1}`,
      type: 'line',
      data: path,
      smooth: true,
      symbol: 'none',
      lineStyle: {
        width: 1,
        opacity: 0.3 + Math.random() * 0.4
      }
    }))
    
    const option = {
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          const day = params[0].axisValue
          let html = `<div style="font-weight:bold;margin-bottom:5px;">第 ${day} 天</div>`
          params.forEach(p => {
            html += `<div>${p.seriesName}: ¥${p.value.toLocaleString()}</div>`
          })
          return html
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'value',
        name: '天数'
      },
      yAxis: {
        type: 'value',
        name: '组合价值 (元)',
        axisLabel: {
          formatter: (value) => {
            if (value >= 10000) {
              return (value / 10000).toFixed(1) + '万'
            }
            return value.toLocaleString()
          }
        }
      },
      series
    }
    
    chart.setOption(option)
    window.addEventListener('resize', () => chart.resize())
    console.log('模拟路径图渲染完成')
  } else {
    console.error('pathChart ref 为空')
  }
}

onMounted(() => {
  runSimulation()
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  padding: 20px;
}
.container { max-width: 1400px; margin: 0 auto; }
.header { text-align: center; color: white; margin-bottom: 30px; }
.header h1 { font-size: 2.5rem; margin-bottom: 10px; }
.header p { font-size: 1.1rem; opacity: 0.9; }
.card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.1);
  margin-bottom: 20px;
}
.card-title {
  font-size: 1.3rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid #eee;
}
.input-group {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}
.input-item { flex: 1; min-width: 200px; }
.input-item label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #555;
}
.input-item input, .input-item select {
  width: 100%;
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.3s;
}
.input-item input:focus, .input-item select:focus {
  outline: none;
  border-color: #667eea;
}
.btn {
  padding: 12px 30px;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}
.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}
.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
}
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}
.metric-card {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
}
.metric-value {
  font-size: 2rem;
  font-weight: 700;
  color: #333;
  margin-bottom: 5px;
}
.metric-label { font-size: 0.9rem; color: #666; }
.risk-rating {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
}
.rating-circle {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.5rem;
  font-weight: 700;
  color: white;
}
.rating-info { text-align: left; }
.rating-label {
  font-size: 1.5rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 5px;
}
.rating-desc { font-size: 0.9rem; color: #666; }
.chart-container { height: 350px; margin-top: 20px; }
.loading {
  text-align: center;
  padding: 40px;
  color: #666;
}
.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
.error-message {
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 15px;
  color: #dc2626;
  margin-bottom: 20px;
}
.text-green { color: #22c55e; }
.text-red { color: #ef4444; }
@media (max-width: 768px) {
  .input-group { flex-direction: column; }
  .header h1 { font-size: 1.8rem; }
}
</style>