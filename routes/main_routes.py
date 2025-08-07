#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主页面路由
"""

from flask import Blueprint, render_template, current_app, request
from services import TradingService, StrategyService, AnalysisService

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """首页"""
    try:
        # 获取服务实例
        trading_service = TradingService(current_app.db_service)
        strategy_service = StrategyService(current_app.db_service)
        analysis_service = AnalysisService(current_app.db_service)
        
        # 获取统计数据
        all_trades = trading_service.get_all_trades()
        strategies_list = strategy_service.get_all_strategies()
        
        # 转换策略为字典格式 (模板期望的格式)
        strategies = {str(s['id']): s['name'] for s in strategies_list}
        strategies['all'] = '所有策略'  # 添加"所有策略"选项
        
        # 计算基础统计
        total_trades = len(all_trades)
        open_trades = len([t for t in all_trades if t['status'] == 'open'])
        closed_trades = len([t for t in all_trades if t['status'] == 'closed'])
        total_strategies = len(strategies_list)
        
        # 计算总体表现
        overall_performance = analysis_service.calculate_strategy_score()
        
        # 获取最近的交易
        recent_trades = all_trades[:10] if all_trades else []
        
        # 获取查询参数
        selected_strategy = request.args.get('strategy', 'all')
        
        # 构建stats对象
        stats = {
            'selected_strategy': selected_strategy,
            'strategy_stats': {}  # 策略统计数据，暂时为空
        }
        
        return render_template('index.html',
                             total_trades=total_trades,
                             open_trades=open_trades,
                             closed_trades=closed_trades,
                             total_strategies=total_strategies,
                             overall_performance=overall_performance,
                             recent_trades=recent_trades,
                             strategies=strategies,
                             stats=stats)
        
    except Exception as e:
        current_app.logger.error(f"首页加载失败: {str(e)}")
        return render_template('index.html',
                             total_trades=0,
                             open_trades=0,
                             closed_trades=0,
                             total_strategies=0,
                             overall_performance={'stats': {}},
                             recent_trades=[],
                             strategies={'all': '所有策略'},
                             stats={'selected_strategy': 'all', 'strategy_stats': {}})
