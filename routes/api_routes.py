#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API路由
"""

from flask import Blueprint, jsonify, request, current_app

from services import StrategyService, AnalysisService
from services.trading_service import TradingService
from utils.decorators import handle_errors

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/strategies')
@handle_errors
def get_strategies():
    """获取所有策略的API"""
    strategy_service = StrategyService(current_app.db_service)
    strategies = strategy_service.get_all_strategies(return_dto=True)
    from services.mappers import dto_list_to_dicts
    return jsonify({'success': True, 'data': dto_list_to_dicts(strategies)})


@api_bp.route('/tags')
@handle_errors
def get_tags():
    """获取所有标签的API"""
    strategy_service = StrategyService(current_app.db_service)
    tags = strategy_service.get_all_tags()
    
    return jsonify({
        'success': True,
        'data': tags
    })


@api_bp.route('/symbol_lookup')
@handle_errors
def symbol_lookup():
    """根据已存在交易记录，通过标的代码查询其常用名称。

    用途：在新建买入时自动回填标的名称。
    """
    symbol_code = request.args.get('symbol_code', '').strip()
    if not symbol_code:
        return jsonify({'success': False, 'message': 'symbol_code 不能为空'}), 400

    db = current_app.db_service
    # 取最近更新的一条记录的名称
    row = db.execute_query(
        """
        SELECT symbol_name
        FROM trades
        WHERE UPPER(symbol_code) = ?
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (symbol_code.upper(),),
        fetch_one=True,
    )

    if row:
        return jsonify({
            'success': True,
            'found': True,
            'data': {
                'symbol_code': symbol_code.upper(),
                'symbol_name': row['symbol_name'],
            }
        })

    return jsonify({'success': True, 'found': False, 'data': {'symbol_code': symbol_code.upper()}})


@api_bp.route('/trade_detail/<int:detail_id>')
@handle_errors
def get_trade_detail(detail_id: int):
    """获取单条交易明细，便于前端弹窗回填。"""
    db = current_app.db_service
    row = db.execute_query(
        '''
        SELECT d.*, t.symbol_code, t.symbol_name
        FROM trade_details d
        LEFT JOIN trades t ON d.trade_id = t.id
        WHERE d.id = ?
        ''',
        (detail_id,),
        fetch_one=True,
    )
    if not row:
        return jsonify({'success': False, 'message': f'明细ID {detail_id} 不存在'}), 404
    return jsonify({'success': True, 'detail': dict(row)})


@api_bp.route('/quick_sell', methods=['POST'])
@handle_errors
def quick_sell():
    """快捷卖出接口。

    要求参数（form 或 json）：
    - trade_id: 交易ID（必填）
    - price: 卖出价格（必填）
    - transaction_date: 卖出日期（必填）
    - quantity: 卖出数量（必填，正整数）
    - transaction_fee: 交易费用（可选，默认0）
    - sell_reason: 卖出理由（可选）
    只会影响对应 trade_id 的那条交易。
    """
    trading_service = TradingService(current_app.db_service)

    form = request.form if not request.is_json else request.json

    trade_id = form.get('trade_id')
    price = form.get('price')
    transaction_date = form.get('transaction_date')
    quantity = form.get('quantity')
    detail_id = form.get('detail_id')
    transaction_fee = form.get('transaction_fee', 0)
    sell_reason = form.get('sell_reason', '')

    # 基本校验
    if not trade_id or not price or not transaction_date:
        return jsonify({'success': False, 'message': 'trade_id、price、transaction_date 为必填'}), 400
    try:
        trade_id = int(trade_id)
    except ValueError:
        return jsonify({'success': False, 'message': 'trade_id 非法'}), 400

    try:
        quantity = int(quantity) if quantity is not None else 0
    except ValueError:
        return jsonify({'success': False, 'message': 'quantity 必须为正整数'}), 400

    if quantity <= 0:
        return jsonify({'success': False, 'message': 'quantity 必须大于 0'}), 400

    # 若提供 detail_id，校验本次卖出份额不超过该买入明细的FIFO剩余
    if detail_id:
        try:
            did = int(detail_id)
        except ValueError:
            return jsonify({'success': False, 'message': 'detail_id 非法'}), 400
        remaining_map = trading_service.compute_buy_detail_remaining_map(trade_id)
        remaining_for_detail = int(remaining_map.get(did, 0))
        if quantity > remaining_for_detail:
            return jsonify({'success': False, 'message': '卖出份额超过该笔买入的可卖剩余'}), 400

    ok, msg = trading_service.add_sell_transaction(
        trade_id=trade_id,
        price=price,
        quantity=quantity,
        transaction_date=transaction_date,
        transaction_fee=transaction_fee,
        sell_reason=sell_reason,
    )

    return jsonify({'success': ok, 'message': msg})


@api_bp.route('/tag/create', methods=['POST'])
@handle_errors
def create_tag():
    """创建标签的API"""
    strategy_service = StrategyService(current_app.db_service)
    
    name = request.form.get('name') or (request.json.get('name') if request.is_json else None)
    
    if not name:
        return jsonify({
            'success': False,
            'message': '标签名称不能为空'
        }), 400
    
    success, message = strategy_service.create_tag(name)
    
    return jsonify({
        'success': success,
        'message': message
    })


@api_bp.route('/tag/<int:tag_id>/update', methods=['POST'])
@handle_errors
def update_tag(tag_id):
    """更新标签的API"""
    strategy_service = StrategyService(current_app.db_service)
    
    # 兼容前端可能传递的 name 或 new_name
    new_name = (
        request.form.get('name')
        or request.form.get('new_name')
        or (request.json.get('name') if request.is_json else None)
        or (request.json.get('new_name') if request.is_json else None)
    )
    
    if not new_name:
        return jsonify({
            'success': False,
            'message': '新标签名称不能为空'
        }), 400
    
    success, message = strategy_service.update_tag(tag_id, new_name)
    
    return jsonify({'success': success, 'message': message})


@api_bp.route('/tag/<int:tag_id>/delete', methods=['POST'])
@handle_errors
def delete_tag(tag_id):
    """删除标签的API"""
    strategy_service = StrategyService(current_app.db_service)
    
    success, message = strategy_service.delete_tag(tag_id)
    
    return jsonify({
        'success': success,
        'message': message
    })


@api_bp.route('/strategy_score')
@handle_errors
def get_strategy_score():
    """获取策略评分的API"""
    analysis_service = AnalysisService(current_app.db_service)
    
    # 获取查询参数
    strategy_id = request.args.get('strategy_id', type=int)
    strategy = request.args.get('strategy')
    symbol_code = request.args.get('symbol_code')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    score = analysis_service.calculate_strategy_score(
        strategy_id=strategy_id,
        strategy=strategy,
        symbol_code=symbol_code,
        start_date=start_date,
        end_date=end_date
    )
    # 统一附加评分字段
    score = analysis_service.attach_score_fields(score)
    
    return jsonify({
        'success': True,
        'data': score
    })


@api_bp.route('/strategy_trend')
@handle_errors
def get_strategy_trend():
    """获取策略趋势数据的API"""
    analysis_service = AnalysisService(current_app.db_service)
    
    strategy_id = request.args.get('strategy_id', type=int)
    period_type = request.args.get('period_type', 'month')  # year, quarter, month
    
    if not strategy_id:
        return jsonify({
            'success': False,
            'message': '策略ID不能为空'
        }), 400
    
    try:
        # 获取时间周期列表
        periods = analysis_service.get_time_periods(period_type)
        
        # 计算每个周期的表现
        trend_data = []
        for period in periods:
            start_date, end_date = analysis_service._get_period_date_range(period, period_type)
            score = analysis_service.calculate_strategy_score(
                strategy_id=strategy_id,
                start_date=start_date,
                end_date=end_date
            )
            
            trend_data.append({
                'period': period,
                'return_rate': score['stats']['total_return_rate'],
                'win_rate': score['stats']['win_rate'],
                'trades_count': score['stats']['total_trades']
            })
        
        # 按时间排序
        trend_data.sort(key=lambda x: x['period'])
        
        return jsonify({
            'success': True,
            'data': trend_data
        })
        
    except Exception as e:
        current_app.logger.error(f"获取策略趋势失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取策略趋势失败: {str(e)}'
        }), 500


@api_bp.errorhandler(404)
def api_not_found(error):
    """API 404错误处理"""
    return jsonify({
        'success': False,
        'message': 'API接口不存在'
    }), 404


@api_bp.errorhandler(405)
def api_method_not_allowed(error):
    """API 405错误处理"""
    return jsonify({
        'success': False,
        'message': '请求方法不被允许'
    }), 405


@api_bp.errorhandler(500)
def api_internal_error(error):
    """API 500错误处理"""
    return jsonify({
        'success': False,
        'message': '服务器内部错误'
    }), 500
