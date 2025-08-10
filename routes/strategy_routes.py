#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略相关路由
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app

from services import StrategyService, TradingService
from utils.decorators import handle_errors

strategy_bp = Blueprint('strategy', __name__)


@strategy_bp.route('/strategies')
def strategies():
    """策略列表页面"""
    try:
        strategy_service = StrategyService(current_app.db_service)
        trading_service = TradingService(current_app.db_service)
        strategies_list = strategy_service.get_all_strategies()

        # 为每个策略添加交易数量
        for strategy in strategies_list:
            trades = trading_service.get_all_trades(strategy=strategy['name'])
            strategy['trade_count'] = len([t for t in trades if t['status'] != 'deleted'])

        # 获取标签并计算使用次数
        tags = strategy_service.get_all_tags()
        usage_rows = strategy_service.db.execute_query(
            'SELECT tag_id, COUNT(*) AS usage_count FROM strategy_tag_relations GROUP BY tag_id'
        )
        tag_id_to_usage = {row['tag_id']: row['usage_count'] for row in usage_rows}
        for tag in tags:
            tag['usage_count'] = int(tag_id_to_usage.get(tag['id'], 0))
        # 内置标签排在自定义标签之前，然后按名称排序
        tags.sort(key=lambda t: (0 if t.get('is_predefined') else 1, t.get('name', '')))

        return render_template('strategies.html', strategies=strategies_list, tags=tags)
        
    except Exception as e:
        current_app.logger.error(f"策略列表加载失败: {str(e)}")
        return render_template('strategies.html', strategies=[], tags=[])


@strategy_bp.route('/strategy/create', methods=['GET', 'POST'])
def create_strategy():
    """创建策略"""
    if request.method == 'GET':
        try:
            strategy_service = StrategyService(current_app.db_service)
            tags_data = strategy_service.get_all_tags()
            return render_template('create_strategy.html', tags=tags_data)
            
        except Exception as e:
            current_app.logger.error(f"创建策略页面加载失败: {str(e)}")
            return render_template('create_strategy.html', tags=[])
    
    elif request.method == 'POST':
        try:
            strategy_service = StrategyService(current_app.db_service)
            
            # 获取表单数据
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            tag_names = request.form.getlist('tag_names')
            
            # 创建策略
            success, message = strategy_service.create_strategy(
                name=name,
                description=description,
                tag_names=tag_names
            )
            
            # 检查是否是AJAX请求
            if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': success, 'message': message})
            else:
                # 传统表单提交，重定向到策略管理页面
                if success:
                    return redirect(url_for('strategy.strategies'))
                else:
                    # 如果失败，返回表单页面并显示错误
                    tags_data = strategy_service.get_all_tags()
                    return render_template('create_strategy.html', tags=tags_data, error=message)
                    
        except Exception as e:
            current_app.logger.error(f"创建策略失败: {str(e)}")
            error_message = f"创建策略失败: {str(e)}"
            
            if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_message}), 500
            else:
                strategy_service = StrategyService(current_app.db_service)
                tags_data = strategy_service.get_all_tags()
                return render_template('create_strategy.html', tags=tags_data, error=error_message)


@strategy_bp.route('/strategy/<int:strategy_id>/edit', methods=['GET', 'POST'])
def edit_strategy(strategy_id):
    """编辑策略"""
    try:
        strategy_service = StrategyService(current_app.db_service)
        trading_service = TradingService(current_app.db_service)
        
        if request.method == 'GET':
            strategy = strategy_service.get_strategy_by_id(strategy_id)
            if not strategy:
                return redirect(url_for('strategy.strategies'))
            
            # 附带统计字段
            trades = trading_service.get_all_trades(strategy=strategy['name'])
            strategy['trade_count'] = len([t for t in trades if t['status'] != 'deleted'])

            tags_data = strategy_service.get_all_tags()
            return render_template('edit_strategy.html', 
                                 strategy=strategy, 
                                 tags=tags_data)
        
        elif request.method == 'POST':
            # 获取表单数据
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            # 前端表单字段名称为 'tags'
            tag_names = request.form.getlist('tags')
            
            # 更新策略
            success, message = strategy_service.update_strategy(
                strategy_id=strategy_id,
                name=name,
                description=description,
                tag_names=tag_names
            )
            
            # 返回JSON以兼容前端fetch提交流程
            return jsonify({'success': success, 'message': message})
                
    except Exception as e:
        current_app.logger.error(f"编辑策略失败: {str(e)}")
        return redirect(url_for('strategy.strategies'))


@strategy_bp.route('/strategy/<int:strategy_id>/delete', methods=['POST'])
@handle_errors
def delete_strategy(strategy_id):
    """删除策略"""
    strategy_service = StrategyService(current_app.db_service)
    
    success, message = strategy_service.delete_strategy(strategy_id)
    
    return jsonify({
        'success': success,
        'message': message
    })
