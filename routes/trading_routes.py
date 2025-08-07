#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易相关路由
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app
from decimal import Decimal

from services import TradingService, StrategyService
from utils.helpers import generate_confirmation_code
from utils.decorators import handle_errors

trading_bp = Blueprint('trading', __name__)


@trading_bp.route('/trades')
def trades():
    """交易列表页面"""
    try:
        trading_service = TradingService(current_app.db_service)
        strategy_service = StrategyService(current_app.db_service)
        
        # 获取筛选参数
        status = request.args.get('status')
        strategy = request.args.get('strategy')
        
        # 获取交易数据
        all_trades = trading_service.get_all_trades(status=status, strategy=strategy)
        strategies_list = strategy_service.get_all_strategies()
        
        # 转换策略为字典格式 (模板期望的格式)
        strategies = {str(s['id']): s['name'] for s in strategies_list}
        strategies['all'] = '所有策略'
        
        return render_template('trades.html', 
                             trades=all_trades, 
                             strategies=strategies,
                             current_status=status,
                             current_strategy=strategy)
        
    except Exception as e:
        current_app.logger.error(f"交易列表加载失败: {str(e)}")
        return render_template('trades.html', trades=[], strategies={'all': '所有策略'})


@trading_bp.route('/add_buy', methods=['GET', 'POST'])
def add_buy():
    """添加买入交易"""
    if request.method == 'GET':
        try:
            strategy_service = StrategyService(current_app.db_service)
            strategies = strategy_service.get_all_strategies()
            return render_template('add_buy.html', strategies_data=strategies)
        except Exception as e:
            current_app.logger.error(f"买入页面加载失败: {str(e)}")
            return render_template('add_buy.html', strategies_data=[])
    
    elif request.method == 'POST':
        try:
            trading_service = TradingService(current_app.db_service)
            
            # 获取表单数据
            strategy_id = int(request.form.get('strategy'))
            symbol_code = request.form.get('symbol_code')
            symbol_name = request.form.get('symbol_name')
            price = Decimal(request.form.get('price', '0'))
            quantity = int(request.form.get('quantity', '0'))
            transaction_date = request.form.get('transaction_date')
            transaction_fee = Decimal(request.form.get('transaction_fee', '0'))
            buy_reason = request.form.get('buy_reason', '')
            
            # 根据策略ID获取策略名称
            strategy_service = StrategyService(current_app.db_service)
            strategy_obj = strategy_service.get_strategy_by_id(strategy_id)
            if not strategy_obj:
                return render_template('add_buy.html', 
                                       strategies_data=strategy_service.get_all_strategies(),
                                       error_message="策略不存在")
            
            # 添加买入交易
            success, result = trading_service.add_buy_transaction(
                strategy=strategy_obj['name'],
                symbol_code=symbol_code,
                symbol_name=symbol_name,
                price=price,
                quantity=quantity,
                transaction_date=transaction_date,
                transaction_fee=transaction_fee,
                buy_reason=buy_reason
            )
            
            if success:
                return redirect(url_for('trading.trades'))
            else:
                strategy_service = StrategyService()
                strategies = strategy_service.get_all_strategies()
                return render_template('add_buy.html', 
                                     strategies=strategies, 
                                     error=result)
                
        except Exception as e:
            current_app.logger.error(f"添加买入交易失败: {str(e)}")
            strategy_service = StrategyService()
            strategies = strategy_service.get_all_strategies()
            return render_template('add_buy.html', 
                                 strategies=strategies, 
                                 error=f"添加买入交易失败: {str(e)}")


@trading_bp.route('/add_sell/<int:trade_id>', methods=['GET', 'POST'])
def add_sell(trade_id):
    """添加卖出交易"""
    if request.method == 'GET':
        try:
            trading_service = TradingService(current_app.db_service)
            trade = trading_service.get_trade_by_id(trade_id)
            
            if not trade:
                return redirect(url_for('trading.trades'))
            
            return render_template('add_sell.html', trade=trade)
            
        except Exception as e:
            current_app.logger.error(f"卖出页面加载失败: {str(e)}")
            return redirect(url_for('trading.trades'))
    
    elif request.method == 'POST':
        try:
            trading_service = TradingService(current_app.db_service)
            
            # 获取表单数据
            price = Decimal(request.form.get('price', '0'))
            quantity = int(request.form.get('quantity', '0'))
            transaction_date = request.form.get('transaction_date')
            transaction_fee = Decimal(request.form.get('transaction_fee', '0'))
            sell_reason = request.form.get('sell_reason', '')
            trade_log = request.form.get('trade_log', '')
            
            # 添加卖出交易
            success, message = trading_service.add_sell_transaction(
                trade_id=trade_id,
                price=price,
                quantity=quantity,
                transaction_date=transaction_date,
                transaction_fee=transaction_fee,
                sell_reason=sell_reason,
                trade_log=trade_log
            )
            
            if success:
                return redirect(url_for('trading.trades'))
            else:
                trade = trading_service.get_trade_by_id(trade_id)
                return render_template('add_sell.html', 
                                     trade=trade, 
                                     error=message)
                
        except Exception as e:
            current_app.logger.error(f"添加卖出交易失败: {str(e)}")
            trading_service = TradingService(current_app.db_service)
            trade = trading_service.get_trade_by_id(trade_id)
            return render_template('add_sell.html', 
                                 trade=trade, 
                                 error=f"添加卖出交易失败: {str(e)}")


@trading_bp.route('/trade_details/<int:trade_id>')
def trade_details(trade_id):
    """交易详情页面"""
    try:
        trading_service = TradingService(current_app.db_service)
        
        trade = trading_service.get_trade_by_id(trade_id)
        if not trade:
            return redirect(url_for('trading.trades'))
        
        details = trading_service.get_trade_details(trade_id)
        modifications = trading_service.get_trade_modifications(trade_id)
        
        return render_template('trade_details.html',
                             trade=trade,
                             details=details,
                             modifications=modifications)
        
    except Exception as e:
        current_app.logger.error(f"交易详情加载失败: {str(e)}")
        return redirect(url_for('trading.trades'))


@trading_bp.route('/edit_trade/<int:trade_id>', methods=['GET', 'POST'])
def edit_trade(trade_id):
    """编辑交易"""
    # 这个功能比较复杂，先创建基础结构
    try:
        trading_service = TradingService()
        
        trade = trading_service.get_trade_by_id(trade_id)
        if not trade:
            return redirect(url_for('trading.trades'))
        
        if request.method == 'GET':
            strategy_service = StrategyService()
            strategies = strategy_service.get_all_strategies()
            details = trading_service.get_trade_details(trade_id)
            
            return render_template('edit_trade.html',
                                 trade=trade,
                                 details=details,
                                 strategies=strategies)
        
        # POST 方法的实现需要更复杂的逻辑，暂时返回基础页面
        return redirect(url_for('trading.trade_details', trade_id=trade_id))
        
    except Exception as e:
        current_app.logger.error(f"编辑交易失败: {str(e)}")
        return redirect(url_for('trading.trades'))


@trading_bp.route('/generate_confirmation_code')
def generate_confirmation_code_endpoint():
    """生成确认码"""
    code = generate_confirmation_code()
    return jsonify({'confirmation_code': code})


@trading_bp.route('/delete_trade/<int:trade_id>', methods=['POST'])
@handle_errors
def delete_trade(trade_id):
    """软删除交易"""
    trading_service = TradingService()
    
    confirmation_code = request.form.get('confirmation_code')
    delete_reason = request.form.get('delete_reason', '')
    operator_note = request.form.get('operator_note', '')
    
    if not confirmation_code:
        return jsonify({'success': False, 'message': '请提供确认码'}), 400
    
    success = trading_service.soft_delete_trade(
        trade_id=trade_id,
        confirmation_code=confirmation_code,
        delete_reason=delete_reason,
        operator_note=operator_note
    )
    
    if success:
        return jsonify({'success': True, 'message': '交易已删除'})
    else:
        return jsonify({'success': False, 'message': '删除失败'}), 500


@trading_bp.route('/deleted_trades')
def deleted_trades():
    """已删除的交易列表"""
    try:
        trading_service = TradingService()
        deleted_trades_list = trading_service.get_deleted_trades()
        
        return render_template('deleted_trades.html', trades=deleted_trades_list)
        
    except Exception as e:
        current_app.logger.error(f"已删除交易列表加载失败: {str(e)}")
        return render_template('deleted_trades.html', trades=[])


@trading_bp.route('/restore_trade/<int:trade_id>', methods=['POST'])
@handle_errors
def restore_trade(trade_id):
    """恢复已删除的交易"""
    trading_service = TradingService()
    
    confirmation_code = request.form.get('confirmation_code')
    operator_note = request.form.get('operator_note', '')
    
    if not confirmation_code:
        return jsonify({'success': False, 'message': '请提供确认码'}), 400
    
    success = trading_service.restore_trade(
        trade_id=trade_id,
        confirmation_code=confirmation_code,
        operator_note=operator_note
    )
    
    if success:
        return jsonify({'success': True, 'message': '交易已恢复'})
    else:
        return jsonify({'success': False, 'message': '恢复失败'}), 500


@trading_bp.route('/permanently_delete_trade/<int:trade_id>', methods=['POST'])
@handle_errors
def permanently_delete_trade(trade_id):
    """永久删除交易"""
    trading_service = TradingService()
    
    confirmation_code = request.form.get('confirmation_code')
    confirmation_text = request.form.get('confirmation_text')
    delete_reason = request.form.get('delete_reason', '')
    operator_note = request.form.get('operator_note', '')
    
    if not confirmation_code or not confirmation_text:
        return jsonify({'success': False, 'message': '请提供确认码和确认文本'}), 400
    
    success = trading_service.permanently_delete_trade(
        trade_id=trade_id,
        confirmation_code=confirmation_code,
        confirmation_text=confirmation_text,
        delete_reason=delete_reason,
        operator_note=operator_note
    )
    
    if success:
        return jsonify({'success': True, 'message': '交易已永久删除'})
    else:
        return jsonify({'success': False, 'message': '删除失败'}), 500
