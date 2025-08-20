#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多策略系统分析 - 主应用文件（重构版）
"""

import os
import tempfile
import time
from flask import Flask

from config import config
from routes import main_bp, trading_bp, strategy_bp, analysis_bp, api_bp, admin_bp, macro_bp, api_macro_bp, meso_bp


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
    app.register_blueprint(admin_bp)
    # 宏观观察体系（MVP）
    app.register_blueprint(macro_bp)
    app.register_blueprint(api_macro_bp)
    # 中观观察体系（全球股指趋势）
    app.register_blueprint(meso_bp)

    # 初始化并挂载服务到 app（供路由通过 current_app 使用）
    from services import DatabaseService, TradingService, StrategyService, AnalysisService
    from services.macro_service import MacroService
    # 在测试环境下为每个 app 实例创建独立的临时数据库文件，避免污染产品库
    db_path = None
    if config_name == 'testing':
        db_path = os.path.join(tempfile.gettempdir(), f"mirror_test_{os.getpid()}_{int(time.time()*1000)}.db")
        macro_db_path = os.path.join(tempfile.gettempdir(), f"mirror_macro_test_{os.getpid()}_{int(time.time()*1000)}.db")
        meso_db_path = os.path.join(tempfile.gettempdir(), f"mirror_meso_test_{os.getpid()}_{int(time.time()*1000)}.db")
        app.config['DB_PATH'] = db_path
        app.config['MACRO_DB_PATH'] = macro_db_path
        app.config['MESO_DB_PATH'] = meso_db_path
    app.db_service = DatabaseService(db_path)
    app.trading_service = TradingService(app.db_service)
    app.strategy_service = StrategyService(app.db_service)
    app.analysis_service = AnalysisService(app.db_service)
    app.macro_service = MacroService(app.db_service)
    # 兼容旧引用
    app.tracker = app.trading_service
    
    # 全局错误处理
    @app.errorhandler(404)
    def page_not_found(error):
        return "页面不存在", 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return "服务器内部错误", 500
    
    return app


# 为了兼容性，创建全局app实例，并导出全局 tracker 引用
app = create_app()
tracker = app.trading_service  # 保持向后兼容


if __name__ == '__main__':
    from config import Config
    app.run(debug=app.config.get('DEBUG', True), host=Config.HOST, port=Config.PORT)
