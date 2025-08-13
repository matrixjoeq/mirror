#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析相关路由
"""

from flask import Blueprint, render_template, request, redirect, url_for, current_app

from services import AnalysisService, StrategyService
from services.mappers import dto_list_to_dicts, to_dict_dataclass
from utils.decorators import handle_errors

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/strategy_scores')
def strategy_scores():
    """策略评分页面"""
    try:
        analysis_service = AnalysisService(current_app.db_service)
        strategy_service = StrategyService(current_app.db_service)
        
        scores_dto = analysis_service.get_strategy_scores(return_dto=True)
        strategies_raw = strategy_service.get_all_strategies(return_dto=True)
        # DTO → dict（模板内按 stats 动态计算评分显示）
        scores_list = [analysis_service.attach_score_fields(to_dict_dataclass(s)) for s in scores_dto]
        strategies = dto_list_to_dicts(strategies_raw)
        # 将评分列表转换为字典格式，模板期望 {strategy_id: score}
        scores = {s['strategy_id']: s for s in scores_list}
        
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
        strategy = strategy_service.get_strategy_by_id(strategy_id, return_dto=True)
        strategy = to_dict_dataclass(strategy) if strategy else None
        if not strategy:
            return redirect(url_for('analysis.strategy_scores'))
        
        # 计算策略评分（DTO）
        score_dto = analysis_service.calculate_strategy_score(strategy_id=strategy_id, return_dto=True)
        strategy_score = analysis_service.attach_score_fields(to_dict_dataclass(score_dto))
        
        # 获取该策略下的股票评分
        sort_by = request.args.get('sort_by', 'total_return_rate')
        sort_order = request.args.get('sort_order', 'desc')
        
        symbol_scores_dto = analysis_service.get_symbol_scores_by_strategy(strategy_id=strategy_id, return_dto=True)
        symbol_scores = [analysis_service.attach_score_fields(to_dict_dataclass(s)) for s in symbol_scores_dto]
        
        # 排序（对可能为 None 的字段进行兜底，避免 None 比较）
        reverse = (sort_order == 'desc')

        def _compute_scores(stats: dict) -> tuple:
            win_rate_score = (stats.get('win_rate') or 0) / 10
            profit_loss_ratio = stats.get('avg_profit_loss_ratio')
            profit_loss_ratio_score = 10 if profit_loss_ratio == 9999.0 else (profit_loss_ratio or 0)
            if profit_loss_ratio_score > 10:
                profit_loss_ratio_score = 10
            avg_holding_days = stats.get('avg_holding_days')
            total_trades = stats.get('total_trades') or 0
            if not total_trades:
                frequency_score = 0
            else:
                if avg_holding_days is None:
                    frequency_score = 0
                elif avg_holding_days <= 1:
                    frequency_score = 8
                elif avg_holding_days <= 7:
                    frequency_score = 7
                elif avg_holding_days <= 30:
                    frequency_score = 6
                else:
                    frequency_score = 6 - ((avg_holding_days - 30) / 30)
            total_score = win_rate_score + profit_loss_ratio_score + frequency_score
            return win_rate_score, profit_loss_ratio_score, frequency_score, total_score

        if sort_by in ['total_return_rate', 'win_rate', 'total_return', 'avg_return_per_trade', 'avg_holding_days', 'total_trades']:
            symbol_scores.sort(key=lambda x: (x.get('stats', {}).get(sort_by) or 0), reverse=reverse)
        elif sort_by in ['total_score', 'win_rate_score', 'profit_loss_ratio_score', 'frequency_score']:
            index_map = {
                'win_rate_score': 0,
                'profit_loss_ratio_score': 1,
                'frequency_score': 2,
                'total_score': 3,
            }
            idx = index_map.get(sort_by, 3)
            symbol_scores.sort(key=lambda x: _compute_scores(x.get('stats', {}))[idx], reverse=reverse)
        elif sort_by == 'symbol_code':
            symbol_scores.sort(key=lambda x: x.get('symbol_code', '') or '', reverse=reverse)
        
        # 获取所有策略用于下拉选择
        strategies = dto_list_to_dicts(strategy_service.get_all_strategies(return_dto=True))
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
        # 提供策略数据给前端，便于渲染与异步评分
        strategy_service = StrategyService(current_app.db_service)
        strategies_data = dto_list_to_dicts(strategy_service.get_all_strategies(return_dto=True))
        
        return render_template('symbol_comparison.html', symbols=symbols, strategies_data=strategies_data)
        
    except Exception as e:
        current_app.logger.error(f"股票对比页面加载失败: {str(e)}")
        return render_template('symbol_comparison.html', symbols=[], strategies_data=[])


@analysis_bp.route('/symbol_detail/<symbol_code>')
def symbol_detail(symbol_code):
    """股票详情页面"""
    try:
        analysis_service = AnalysisService(current_app.db_service)

        # 获取该股票在各策略下的表现（DTO）并统一附加评分字段
        scores_dto = analysis_service.get_strategies_scores_by_symbol(symbol_code, return_dto=True)
        strategy_scores = [analysis_service.attach_score_fields(to_dict_dataclass(s)) for s in scores_dto]

        if not strategy_scores:
            return redirect(url_for('analysis.symbol_comparison'))

        # 旧字段兼容逻辑已移除，模板直接使用 DTO 字段

        # 获取股票名称（从评分数据推断）
        symbol_name = next((s.get('symbol_name') for s in strategy_scores if s.get('symbol_name')), '未知股票')

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
        strategy_service = StrategyService(current_app.db_service)
        
        # 获取时间粒度参数
        period_type = request.args.get('period_type', 'year')
        
        # 获取时间周期
        years = analysis_service.get_time_periods('year')
        quarters = analysis_service.get_time_periods('quarter')
        months = analysis_service.get_time_periods('month')
        strategies_data = strategy_service.get_all_strategies()
        
        # 根据粒度选择展示的周期列表
        if period_type == 'quarter':
            periods = quarters
        elif period_type == 'month':
            periods = months
        else:
            period_type = 'year'
            periods = years
        
        return render_template('time_comparison.html',
                             years=years,
                             quarters=quarters,
                             months=months,
                             strategies_data=strategies_data,
                             periods=periods,
                             period_type=period_type)
        
    except Exception as e:
        current_app.logger.error(f"时间对比页面加载失败: {str(e)}")
        return render_template('time_comparison.html', 
                             years=[], quarters=[], months=[], strategies_data=[], periods=[], period_type='year')


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

        # 计算开始和结束日期
        start_date, end_date = analysis_service._get_period_date_range(period, period_type)

        # 获取该时间段的策略表现
        scores_dto = analysis_service.get_strategies_scores_by_time_period(period, period_type, return_dto=True)
        strategy_scores = [analysis_service.attach_score_fields(to_dict_dataclass(s)) for s in scores_dto]

        # 获取时间段汇总
        ps_dto = analysis_service.get_period_summary(period, period_type, return_dto=True)
        period_summary = to_dict_dataclass(ps_dto)

        return render_template('time_detail.html',
                              period=period,
                              period_type=period_type,
                              start_date=start_date,
                              end_date=end_date,
                              strategy_scores=strategy_scores,
                              period_summary=period_summary)
        
    except Exception as e:
        current_app.logger.error(f"时间段详情页面加载失败: {str(e)}")
        return redirect(url_for('analysis.time_comparison'))
