#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析相关路由
"""

from flask import Blueprint, render_template, request, redirect, url_for, current_app

from services import AnalysisService, StrategyService
from utils.decorators import handle_errors

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/strategy_scores')
def strategy_scores():
    """策略评分页面"""
    try:
        analysis_service = AnalysisService(current_app.db_service)
        strategy_service = StrategyService(current_app.db_service)
        
        scores_list = analysis_service.get_strategy_scores()
        strategies = strategy_service.get_all_strategies()
        
        # 为向后兼容，为每个评分添加旧字段
        for score in scores_list:
            stats = score['stats']
            # 计算旧评分字段
            score['win_rate_score'] = min(stats['win_rate'] / 10, 10)  # 胜率百分比除以10
            
            # 盈亏比评分：基于总收益率的简化计算
            if stats['total_return_rate'] <= 0:
                score['profit_loss_ratio_score'] = 0
            else:
                score['profit_loss_ratio_score'] = min(stats['total_return_rate'] / 10, 10)
            
            # 频率评分：基于平均持仓天数
            if stats['avg_holding_days'] <= 1:
                score['frequency_score'] = 8
            elif stats['avg_holding_days'] <= 7:
                score['frequency_score'] = 7
            elif stats['avg_holding_days'] <= 30:
                score['frequency_score'] = 6
            else:
                score['frequency_score'] = max(0, 6 - (stats['avg_holding_days'] - 30) / 30)
            
            # 总分
            score['total_score'] = score['win_rate_score'] + score['profit_loss_ratio_score'] + score['frequency_score']
        
        # 将评分列表转换为字典格式，模板期望 {strategy_id: score}
        scores = {score['strategy_id']: score for score in scores_list}
        
        return render_template('strategy_scores.html', 
                             scores=scores, 
                             strategies=strategies)
        
    except Exception as e:
        current_app.logger.error(f"策略评分页面加载失败: {str(e)}")
        return render_template('strategy_scores.html', scores={}, strategies=[])


@analysis_bp.route('/strategy_detail/<int:strategy_id>')
def strategy_detail(strategy_id):
    """策略详情页面"""
    try:
        analysis_service = AnalysisService(current_app.db_service)
        strategy_service = StrategyService(current_app.db_service)
        
        # 获取策略信息
        strategy = strategy_service.get_strategy_by_id(strategy_id)
        if not strategy:
            return redirect(url_for('analysis.strategy_scores'))
        
        # 计算策略评分
        strategy_score = analysis_service.calculate_strategy_score(strategy_id=strategy_id)
        
        # 为向后兼容，添加旧的评分字段
        if 'stats' in strategy_score:
            stats = strategy_score['stats']
            # 计算旧评分字段
            strategy_score['win_rate_score'] = min(stats['win_rate'] / 10, 10)  # 胜率百分比除以10
            
            # 盈亏比评分：基于总收益率的简化计算
            if stats['total_return_rate'] <= 0:
                strategy_score['profit_loss_ratio_score'] = 0
            else:
                strategy_score['profit_loss_ratio_score'] = min(stats['total_return_rate'] / 10, 10)
            
            # 频率评分：基于平均持仓天数
            if stats['avg_holding_days'] <= 1:
                strategy_score['frequency_score'] = 8
            elif stats['avg_holding_days'] <= 7:
                strategy_score['frequency_score'] = 7
            elif stats['avg_holding_days'] <= 30:
                strategy_score['frequency_score'] = 6
            else:
                strategy_score['frequency_score'] = max(0, 6 - (stats['avg_holding_days'] - 30) / 30)
            
            # 总分
            strategy_score['total_score'] = strategy_score['win_rate_score'] + strategy_score['profit_loss_ratio_score'] + strategy_score['frequency_score']
        
        # 获取该策略下的股票评分
        sort_by = request.args.get('sort_by', 'total_return_rate')
        sort_order = request.args.get('sort_order', 'desc')
        
        symbol_scores = analysis_service.get_symbol_scores_by_strategy(strategy_id=strategy_id)
        
        # 为symbol_scores中的每个记录添加评分字段以支持排序
        for score in symbol_scores:
            if 'stats' in score:
                stats = score['stats']
                score['win_rate_score'] = min(stats['win_rate'] / 10, 10)
                if stats['total_return_rate'] <= 0:
                    score['profit_loss_ratio_score'] = 0
                else:
                    score['profit_loss_ratio_score'] = min(stats['total_return_rate'] / 10, 10)
                if stats['avg_holding_days'] <= 1:
                    score['frequency_score'] = 8
                elif stats['avg_holding_days'] <= 7:
                    score['frequency_score'] = 7
                elif stats['avg_holding_days'] <= 30:
                    score['frequency_score'] = 6
                else:
                    score['frequency_score'] = max(0, 6 - (stats['avg_holding_days'] - 30) / 30)
                score['total_score'] = score['win_rate_score'] + score['profit_loss_ratio_score'] + score['frequency_score']
        
        # 排序
        reverse = (sort_order == 'desc')
        if sort_by in ['total_return_rate', 'win_rate', 'total_return', 'avg_return_per_trade']:
            symbol_scores.sort(key=lambda x: x['stats'][sort_by], reverse=reverse)
        elif sort_by in ['total_score', 'win_rate_score', 'profit_loss_ratio_score', 'frequency_score']:
            symbol_scores.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
        elif sort_by == 'symbol_code':
            symbol_scores.sort(key=lambda x: x.get('symbol_code', ''), reverse=reverse)
        
        # 获取所有策略用于下拉选择
        strategies = strategy_service.get_all_strategies()
        strategies_dict = {s['id']: s['name'] for s in strategies}
        
        return render_template('strategy_detail.html',
                             strategy_id=strategy_id,
                             strategy=strategy,
                             strategy_name=strategy['name'],
                             strategy_score=strategy_score,
                             symbol_scores=symbol_scores,
                             sort_by=sort_by,
                             sort_order=sort_order,
                             strategies=strategies_dict)
        
    except Exception as e:
        current_app.logger.error(f"策略详情页面加载失败: {str(e)}")
        return redirect(url_for('analysis.strategy_scores'))


@analysis_bp.route('/symbol_comparison')
def symbol_comparison():
    """股票对比页面"""
    try:
        analysis_service = AnalysisService(current_app.db_service)
        symbols = analysis_service.get_all_symbols()
        
        return render_template('symbol_comparison.html', symbols=symbols)
        
    except Exception as e:
        current_app.logger.error(f"股票对比页面加载失败: {str(e)}")
        return render_template('symbol_comparison.html', symbols=[])


@analysis_bp.route('/symbol_detail/<symbol_code>')
def symbol_detail(symbol_code):
    """股票详情页面"""
    try:
        analysis_service = AnalysisService(current_app.db_service)
        
        # 获取该股票在各策略下的表现
        strategy_scores = analysis_service.get_strategies_scores_by_symbol(symbol_code)
        
        if not strategy_scores:
            return redirect(url_for('analysis.symbol_comparison'))
        
        # 获取股票名称（从第一个策略评分中获取）
        symbol_name = "未知股票"
        if strategy_scores:
            # 从trades表中获取股票名称
            from services import TradingService
            trading_service = TradingService()
            trades = trading_service.get_all_trades()
            for trade in trades:
                if trade['symbol_code'] == symbol_code:
                    symbol_name = trade['symbol_name']
                    break
        
        return render_template('symbol_detail.html',
                             symbol_code=symbol_code,
                             symbol_name=symbol_name,
                             strategy_scores=strategy_scores)
        
    except Exception as e:
        current_app.logger.error(f"股票详情页面加载失败: {str(e)}")
        return redirect(url_for('analysis.symbol_comparison'))


@analysis_bp.route('/time_comparison')
def time_comparison():
    """时间对比页面"""
    try:
        analysis_service = AnalysisService(current_app.db_service)
        
        # 获取时间周期
        years = analysis_service.get_time_periods('year')
        quarters = analysis_service.get_time_periods('quarter')
        months = analysis_service.get_time_periods('month')
        
        return render_template('time_comparison.html',
                             years=years,
                             quarters=quarters,
                             months=months)
        
    except Exception as e:
        current_app.logger.error(f"时间对比页面加载失败: {str(e)}")
        return render_template('time_comparison.html', 
                             years=[], quarters=[], months=[])


@analysis_bp.route('/time_detail/<period>')
def time_detail(period):
    """时间段详情页面"""
    try:
        analysis_service = AnalysisService(current_app.db_service)
        
        # 判断周期类型
        period_type = 'year'
        if '-Q' in period:
            period_type = 'quarter'
        elif period.count('-') == 1 and len(period) == 7:
            period_type = 'month'
        
        # 获取该时间段的策略表现
        strategy_scores = analysis_service.get_strategies_scores_by_time_period(period, period_type)
        
        # 获取时间段汇总
        period_summary = analysis_service.get_period_summary(period, period_type)
        
        return render_template('time_detail.html',
                             period=period,
                             period_type=period_type,
                             strategy_scores=strategy_scores,
                             period_summary=period_summary)
        
    except Exception as e:
        current_app.logger.error(f"时间段详情页面加载失败: {str(e)}")
        return redirect(url_for('analysis.time_comparison'))
