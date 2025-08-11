#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主页面路由
"""

from flask import Blueprint, render_template, current_app, request
from services import TradingService, StrategyService, AnalysisService
from decimal import Decimal

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """首页"""
    try:
        # 获取服务实例
        trading_service = TradingService(current_app.db_service)
        strategy_service = StrategyService(current_app.db_service)
        analysis_service = AnalysisService(current_app.db_service)
        
        # 获取统计数据（统一接口）
        all_trades = trading_service.get_all_trades()
        strategies_list = strategy_service.get_all_strategies()
        
        # 转换策略为字典格式 (模板期望的格式)
        strategies = {str(s['id']): s['name'] for s in strategies_list}
        
        # 计算基础统计
        total_trades = len(all_trades)
        open_trades = len([t for t in all_trades if t['status'] == 'open'])
        closed_trades = len([t for t in all_trades if t['status'] == 'closed'])
        total_strategies = len(strategies_list)
        
        # 计算总体表现
        overall_performance = analysis_service.calculate_strategy_score()
        
        # 获取最近的交易（按开仓日期降序取前10）
        recent_trades = trading_service.get_all_trades(order_by='t.open_date DESC', limit=10)
        
        # 获取查询参数
        selected_strategy = request.args.get('strategy', 'all')
        # 若选择了具体策略，按策略过滤统计
        if selected_strategy != 'all' and selected_strategy in strategies:
            filtered_trades = [t for t in all_trades if str(t['strategy_id']) == selected_strategy]
        else:
            filtered_trades = all_trades
        
        # 计算总净利润与总净利率（与服务层统一口径）
        total_net_profit = sum([float(t.get('total_net_profit', 0) or 0) for t in filtered_trades])
        # 分母：各笔交易已卖出部分的不含费买入成本之和
        total_net_profit_denom = 0.0
        for t in filtered_trades:
            try:
                ov = trading_service.get_trade_overview_metrics(t['id'])
                # buy_cost_for_sold = avg_buy_ex * sell_qty
                total_net_profit_denom += float(ov.get('avg_buy_ex', 0.0)) * float(ov.get('sell_qty', 0) or 0)
            except Exception:
                continue
        total_net_profit_pct = (total_net_profit / total_net_profit_denom * 100.0) if total_net_profit_denom > 0 else 0.0

        # 构建stats对象
        stats = {
            'selected_strategy': selected_strategy,
            'total_trades': len(filtered_trades),
            'open_trades': len([t for t in filtered_trades if t['status'] == 'open']),
            'closed_trades': len([t for t in filtered_trades if t['status'] == 'closed']),
            'total_profit_loss': float(sum([t.get('total_profit_loss', 0) or 0 for t in filtered_trades])),
            'total_net_profit': float(total_net_profit),
            'total_net_profit_pct': float(total_net_profit_pct),
            'recent_trades': recent_trades,
            'strategy_stats': {}
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
                             strategies={},
                             stats={'selected_strategy': 'all', 'strategy_stats': {}, 'total_trades': 0, 'open_trades': 0, 'closed_trades': 0, 'total_profit_loss': 0.0, 'recent_trades': []})
