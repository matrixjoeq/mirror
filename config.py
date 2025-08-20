#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多策略系统分析 - 配置管理
"""

import os
from pathlib import Path

class Config:
    """应用配置类"""
    
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'trend_trading_tracker_2024'
    # 服务器配置
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 8383))
    
    # 数据库配置
    BASE_DIR = Path(__file__).parent
    DB_PATH = os.environ.get('DB_PATH') or str(BASE_DIR / 'database' / 'trading_tracker.db')
    # 宏观观察系统独立数据库（与交易跟踪系统完全隔离）
    MACRO_DB_PATH = os.environ.get('MACRO_DB_PATH') or str(BASE_DIR / 'database' / 'macro_observation.db')
    # 中观观察系统独立数据库
    MESO_DB_PATH = os.environ.get('MESO_DB_PATH') or str(BASE_DIR / 'database' / 'meso_observation.db')
    
    # Flask配置
    JSON_AS_ASCII = False
    JSONIFY_PRETTYPRINT_REGULAR = True
    
    # 应用配置
    DEFAULT_STRATEGY = 'trend'
    CONFIRMATION_CODE_LENGTH = 6
    
    # 分页配置
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 200
    
    # 时间格式配置
    DATE_FORMAT = '%Y-%m-%d'
    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    @classmethod
    def init_app(cls, app):
        """初始化Flask应用配置"""
        app.config.from_object(cls)

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    # 默认使用内存数据库（在 app 工厂中会进一步为每个实例分配临时文件，避免并发连接问题）
    DB_PATH = ':memory:'
    MACRO_DB_PATH = ':memory:'
    MESO_DB_PATH = ':memory:'

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
