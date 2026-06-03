🚀 启动步骤---方案一
第一步：启动后端服务（终端 1）
1. cd D:\stock_mvp\montecarlo-risk-analyzer\backend
2. $env:TUSHARE_TOKEN = "98cf930ca6e181e63f7e2a06e000d3bffc0e2fbda56b2fd6435da46b"
3. python app.py
. 等待显示 Running on http://127.0.0.1:5001

第二步：启动前端服务（终端 2）
1. cd D:\stock_mvp\montecarlo-risk-analyzer\frontend
2. npm run dev
. 等待显示 Local: http://localhost:5173/

第三步：打开浏览器访问
http://localhost:5173/

方案二：
快捷启动脚本（可选）
你可以创建一个 .bat 批处理文件来一键启动：
start_montecarlo.bat 
 1. @echo off
 2. echo 启动后端服务...
 3. start cmd /k "cd D:\stock_mvp\montecarlo-risk-analyzer\backend && set TUSHARE_TOKEN=98cf930ca6e181e63f7e2a06e000d3bffc0e2fbda56b2fd6435da46b && python app.py"
 
 5. timeout /t 3 /nobreak >nul
 6. echo 启动前端服务...
 7. start cmd /k "cd D:\stock_mvp\montecarlo-risk-analyzer\frontend && npm run dev"
 8. timeout /t 5 /nobreak >nul
 9. echo 打开浏览器...
 10. start http://localhost:5173/

使用方法：
1. 双击运行 start_montecarlo.bat
2. 会自动打开两个终端窗口和浏览器


总结：每次使用只需打开两个终端，分别运行后端和前端命令，然后打开浏览器即可！ ✅