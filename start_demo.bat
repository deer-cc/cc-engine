@echo off
rem 客服引擎一键启动 (Windows)
rem 用法: 双击运行, 或 cmd 里 start_demo.bat
rem 起来后: http://127.0.0.1:8899  (浏览器打开演示页 / 用 curl 调 API)

cd /d "%~dp0"

echo 正在启动客服引擎 (127.0.0.1:8899) ...
echo 关闭服务: 在本窗口按 Ctrl+C, 或关掉本窗口

rem 先杀掉可能占着端口的旧进程, 避免启动失败
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8899" ^| findstr "LISTENING"') do (
    echo 杀掉占用 8899 的旧进程 PID=%%a
    taskkill /F /PID %%a >nul 2>&1
)

python -m uvicorn src.main:app --host 127.0.0.1 --port 8899
