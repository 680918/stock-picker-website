document.addEventListener('DOMContentLoaded', () => {
    const buttons = document.querySelectorAll('.strategy-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadStrategy(btn.dataset.strategy);
        });
    });
    
    loadStrategy('strategy1');
});

async function loadStrategy(strategy) {
    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').style.display = 'none';
    
    try {
        const response = await fetch(`data/${strategy}.json`);
        const data = await response.json();
        
        displayResults(data);
    } catch (error) {
        document.getElementById('loading').innerHTML = '加载失败，请稍后重试';
    }
}

function displayResults(data) {
    document.getElementById('loading').style.display = 'none';
    
    const summary = document.getElementById('summary');
    const tbody = document.getElementById('stock-body');
    const updateTime = document.getElementById('update-time');
    
    summary.innerHTML = `<strong>📊 ${data.message}</strong>`;
    
    tbody.innerHTML = '';
    data.stocks.forEach(stock => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${stock.代码}</td>
            <td><strong>${stock.名称}</strong></td>
            <td>${stock.行业 || '-'}</td>
            <td><strong style="color: ${stock.得分 > 8 ? '#2e7d32' : stock.得分 > 5 ? '#ff9800' : '#c62828'}">${stock.得分}</strong></td>
            <td>${stock.最新价 || '-'}</td>
            <td>${stock.标签 ? stock.标签.split('|').map(t => '<span class="tag">' + t + '</span>').join('') : '-'}</td>
        `;
        tbody.appendChild(row);
    });
    
    updateTime.textContent = new Date().toLocaleString('zh-CN');
    document.getElementById('results').style.display = 'block';
}
