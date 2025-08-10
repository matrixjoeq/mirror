#!/usr/bin/env bash

# 多策略系统分析 启动脚本
set -euo pipefail

echo "🚀 多策略系统分析 启动中..."

# 选择 Python 解释器（优先 python3）
if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

# 检查并激活已有 venv（不自动创建）
if [ -f "venv/bin/activate" ]; then
  echo "🔄 检测到 venv，正在激活..."
  # shellcheck disable=SC1091
  source venv/bin/activate
else
  echo "⚠️  未检测到 venv，将直接使用系统 Python 运行（不自动创建）。"
fi

# 依赖检查（若缺失 Flask 则安装 requirements）
echo "🔎 检查依赖..."
if ! $PY -m pip show flask >/dev/null 2>&1; then
  echo "📚 安装依赖包..."
  $PY -m pip install -r requirements.txt
fi

# 启动应用
echo "🌐 启动Web应用..."
echo "📍 访问地址: http://127.0.0.1:8383"
echo "⌨️  按 Ctrl+C 停止应用"
echo ""

$PY app.py