#!/bin/bash

# 趋势交易跟踪系统启动脚本

echo "🚀 趋势交易跟踪系统启动中..."

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔄 激活虚拟环境..."
source venv/bin/activate

# 检查依赖是否已安装
if [ ! -f "venv/lib/python*/site-packages/flask/__init__.py" ]; then
    echo "📚 安装依赖包..."
    python3 -m pip install -r requirements.txt
fi

# 启动应用
echo "🌐 启动Web应用..."
echo "📍 访问地址: http://127.0.0.1:8383"
echo "⌨️  按 Ctrl+C 停止应用"
echo ""

python3 app.py