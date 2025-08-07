"""
路由模块
"""

from .main_routes import main_bp
from .trading_routes import trading_bp
from .strategy_routes import strategy_bp
from .analysis_routes import analysis_bp
from .api_routes import api_bp

__all__ = [
    'main_bp',
    'trading_bp', 
    'strategy_bp',
    'analysis_bp',
    'api_bp'
]
