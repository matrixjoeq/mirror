#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势交易跟踪系统 - 配置管理
"""

import os
from pathlib import Path

class Config:
    """应用配置类"""
    
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'trend_trading_tracker_2024'
    
    # 数据库配置
    BASE_DIR = Path(__file__).parent
    DB_PATH = os.environ.get('DB_PATH') or str(BASE_DIR / 'database' / 'trading_tracker.db')
    
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
    # 使用内存数据库进行测试
    DB_PATH = ':memory:'

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
