#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势交易跟踪系统 - 主应用文件（重构版）
"""

import os
from flask import Flask

from config import config
from routes import main_bp, trading_bp, strategy_bp, analysis_bp, api_bp


def create_app(config_name=None):
    """应用工厂函数"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # 注册蓝图
    app.register_blueprint(main_bp)
    app.register_blueprint(trading_bp)
    app.register_blueprint(strategy_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(api_bp)
    
    # 全局错误处理
    @app.errorhandler(404)
    def page_not_found(error):
        return "页面不存在", 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return "服务器内部错误", 500
    
    return app


# 为了兼容性，创建全局app实例
app = create_app()

# 为了兼容性，创建全局tracker实例
from services import DatabaseService, TradingService, StrategyService, AnalysisService

# 初始化服务
db_service = DatabaseService()
tracker = TradingService(db_service)  # 保持向后兼容


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
