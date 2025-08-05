@echo off
chcp 65001 > nul
echo 🚀 趋势交易跟踪系统启动中...

REM 检查虚拟环境是否存在
if not exist "venv" (
    echo 📦 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
echo 🔄 激活虚拟环境...
call venv\Scripts\activate.bat

REM 检查依赖是否已安装
if not exist "venv\Lib\site-packages\flask" (
    echo 📚 安装依赖包...
    python -m pip install -r requirements.txt
)

REM 启动应用
echo 🌐 启动Web应用...
echo 📍 访问地址: http://127.0.0.1:8383
echo ⌨️  按 Ctrl+C 停止应用
echo.

python app.py

pause