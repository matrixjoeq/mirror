"""
路由模块
"""

from .main_routes import main_bp
from .trading_routes import trading_bp
from .strategy_routes import strategy_bp
from .analysis_routes import analysis_bp
from .macro_routes import macro_bp
from .api_macro import api_macro_bp
from .admin_routes import admin_bp
from .api_routes import api_bp

__all__ = [
    'main_bp',
    'trading_bp', 
    'strategy_bp',
    'analysis_bp',
    'macro_bp',
    'api_macro_bp',
    'api_bp',
    'admin_bp'
]
