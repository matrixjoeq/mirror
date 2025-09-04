#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API路由
"""

from flask import Blueprint, jsonify, request, current_app
from typing import Any, cast

from services import StrategyService, AnalysisService
from services.meso_service import MesoService
from services.trading_service import TradingService
from utils.decorators import handle_errors

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/strategies')
@handle_errors
def get_strategies():
    """获取所有策略的API"""
    app = cast(Any, current_app)
    strategy_service = StrategyService(app.db_service)
    strategies = strategy_service.get_all_strategies(return_dto=True)
    from services.mappers import dto_list_to_dicts
    return jsonify({'success': True, 'data': dto_list_to_dicts(strategies)})


@api_bp.route('/tags')
@handle_errors
def get_tags():
    """获取所有标签的API"""
    app = cast(Any, current_app)
    strategy_service = StrategyService(app.db_service)
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

    app = cast(Any, current_app)
    db = app.db_service
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
    app = cast(Any, current_app)
    db = app.db_service
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
    app = cast(Any, current_app)
    trading_service = TradingService(app.db_service)

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


@api_bp.route('/modify_trade_detail', methods=['POST'])
@handle_errors
def modify_trade_detail():
    """修改一条交易明细（价格、数量、手续费、理由等）。

    前端来自 trade_details.html 的模态框提交。
    为了兼容现有服务更新接口，这里根据 detail_id 反查 trade_id，
    然后调用 TradingService.update_trade_record(trade_id, [update_dict]).
    """
    app = cast(Any, current_app)
    db = app.db_service

    form = request.form if not request.is_json else request.json
    detail_id = form.get('detail_id')
    if not detail_id:
        return jsonify({'success': False, 'message': 'detail_id 不能为空'}), 400
    try:
        detail_id_int = int(detail_id)
    except Exception:
        return jsonify({'success': False, 'message': 'detail_id 非法'}), 400

    # 反查 trade_id
    row = db.execute_query(
        'SELECT trade_id FROM trade_details WHERE id = ?',
        (detail_id_int,),
        fetch_one=True,
    )
    if not row:
        return jsonify({'success': False, 'message': f'明细ID {detail_id_int} 不存在'}), 404
    trade_id = int(row['trade_id'])

    # 采集更新字段（仅传递有值的字段）
    def _get_opt(name):
        v = form.get(name)
        return v if v not in (None, '') else None

    update = {'detail_id': detail_id_int}
    price = _get_opt('price')
    quantity = _get_opt('quantity')
    transaction_fee = _get_opt('transaction_fee')
    buy_reason = _get_opt('buy_reason')
    sell_reason = _get_opt('sell_reason')

    if price is not None:
        update['price'] = price
    if quantity is not None:
        update['quantity'] = quantity
    if transaction_fee is not None:
        update['transaction_fee'] = transaction_fee
    if buy_reason is not None:
        update['buy_reason'] = buy_reason
    if sell_reason is not None:
        update['sell_reason'] = sell_reason

    trading_service = TradingService(app.db_service)
    ok, msg = trading_service.update_trade_record(trade_id, [update])
    return jsonify({'success': ok, 'message': msg})


@api_bp.route('/tag/create', methods=['POST'])
@handle_errors
def create_tag():
    """创建标签的API"""
    app = cast(Any, current_app)
    strategy_service = StrategyService(app.db_service)

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
    app = cast(Any, current_app)
    strategy_service = StrategyService(app.db_service)

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
    app = cast(Any, current_app)
    analysis_service = AnalysisService(app.db_service)

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
    app = cast(Any, current_app)
    analysis_service = AnalysisService(app.db_service)

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

        # 计算每个周期的表现（附带统一评分字段，便于前端绘制总分趋势）
        trend_data = []
        for period in periods:
            start_date, end_date = analysis_service._get_period_date_range(period, period_type)
            score = analysis_service.calculate_strategy_score(
                strategy_id=strategy_id,
                start_date=start_date,
                end_date=end_date
            )
            score = analysis_service.attach_score_fields(score)

            trend_data.append({
                'period': period,
                'return_rate': score['stats']['total_return_rate'],
                'win_rate': score['stats']['win_rate'],
                'trades_count': score['stats']['total_trades'],
                'total_score': score['total_score']
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


# ---- 中观观察：全球股指趋势 API ----

@api_bp.route('/meso/indexes')
@handle_errors
def get_meso_indexes():
    svc = MesoService()
    return jsonify({'success': True, 'data': svc.list_indexes()})


@api_bp.route('/meso/trend_series')
@handle_errors
def get_meso_trend_series():
    symbol = request.args.get('symbol', '^GSPC')
    window = request.args.get('window', '3y')
    currency = request.args.get('currency', 'USD')
    svc = MesoService()
    return jsonify({'success': True, 'data': svc.get_trend_series(symbol, window, currency)})


@api_bp.route('/meso/compare_series')
@handle_errors
def get_meso_compare_series():
    symbols_raw = request.args.get('symbols', '^GSPC,^NDX')
    symbols = [s.strip() for s in symbols_raw.split(',') if s.strip()]
    if len(symbols) == 0 or len(symbols) > 10:
        return jsonify({'success': False, 'message': 'symbols must be 1..10'}), 400
    window = request.args.get('window', '3y')
    currency = request.args.get('currency', 'USD')
    svc = MesoService()
    return jsonify({'success': True, 'data': svc.get_compare_series(symbols, window, currency)})


@api_bp.route('/meso/refresh', methods=['POST'])
@handle_errors
def meso_refresh():
    symbols_raw = request.args.get('symbols') or (request.json.get('symbols') if request.is_json else None)
    symbols = None
    if symbols_raw:
        if isinstance(symbols_raw, str):
            symbols = [s.strip() for s in symbols_raw.split(',') if s.strip()]
        elif isinstance(symbols_raw, list):
            symbols = [str(s).strip() for s in symbols_raw if str(s).strip()]
    period = request.args.get('period', '3y')
    svc = MesoService()
    # 统一从全局起始日期开始，服务内仍做去重与仅插入未存日期
    try:
        since = svc.repo.get_global_start_date()
    except Exception:
        since = None
    result = svc.refresh_prices_and_scores(symbols=symbols, period=period, since=since)
    return jsonify({'success': True, 'data': result})


@api_bp.route('/meso/delete_symbol', methods=['POST'])
@handle_errors
def meso_delete_symbol():
    symbol = request.args.get('symbol') or (request.json.get('symbol') if request.is_json else None)
    if not symbol:
        return jsonify({'success': False, 'message': 'symbol is required'}), 400
    remove_meta = request.args.get('remove_meta') or (request.json.get('remove_meta') if request.is_json else None)
    remove_meta = str(remove_meta).lower() in ('1','true','yes','on')
    repo = MesoService().repo
    result = repo.delete_symbol_data(symbol)
    meta_deleted = 0
    if remove_meta:
        meta_deleted = repo.delete_index_metadata(symbol)
    return jsonify({'success': True, 'message': f"deleted total: {result.get('total',0)}", 'detail': result, 'metadata_deleted': meta_deleted})


# ---- 资产大类横向排名（强制 USD / 共同开市日 / 统一价格指标） ----

@api_bp.route('/meso/rankings/asset_class')
@handle_errors
def get_meso_asset_class_rankings():
    asof = request.args.get('asof')
    top = request.args.get('top', type=int) or 10
    return_mode = request.args.get('return_mode', 'price')  # price|total
    svc = MesoService()
    data = svc.get_asset_class_rankings(asof=asof, top=top, return_mode=return_mode)
    return jsonify({'success': True, 'data': data})


@api_bp.route('/meso/instruments')
@handle_errors
def meso_instruments():
    svc = MesoService()
    data = svc.get_instruments_overview()
    return jsonify({'success': True, 'data': data})


@api_bp.route('/meso/instruments', methods=['POST'])
@handle_errors
def meso_instruments_upsert():
    """新增/更新观察对象（标的）。

    接收 JSON 或表单：symbol, name, currency, region, market, asset_class, category, subcategory, provider, instrument_type, is_active
    provider 允许：FRED, YAHOO, SINA, EASTMONEY；instrument_type 允许：index, etf, stock, commodity, bond_yield
    """
    svc = MesoService()
    form = request.form if not request.is_json else request.json
    if not form:
        return jsonify({'success': False, 'message': 'empty payload'}), 400
    allowed = {'FRED', 'YAHOO', 'SINA', 'EASTMONEY'}
    provider = (form.get('provider') or '').upper()
    if provider and provider not in allowed:
        return jsonify({'success': False, 'message': f'provider must be one of {sorted(allowed)}'}), 400
    inst_allowed = {'INDEX','ETF','STOCK','COMMODITY','BOND_YIELD'}
    instrument_type = (form.get('instrument_type') or '').upper()
    if instrument_type and instrument_type not in inst_allowed:
        return jsonify({'success': False, 'message': f'instrument_type must be one of {sorted(inst_allowed)}'}), 400
    symbol = (form.get('symbol') or '').strip()
    if not symbol:
        return jsonify({'success': False, 'message': 'symbol is required'}), 400
    payload_item = {
        'symbol': symbol,
        'name': form.get('name'),
        'currency': form.get('currency'),
        'region': form.get('region'),
        'market': form.get('market'),
        'asset_class': form.get('asset_class'),
        'category': form.get('category'),
        'subcategory': form.get('subcategory'),
        'provider': provider or None,
        'instrument_type': instrument_type or None,
        'use_adjusted': True,
        'always_full_refresh': False,
        'benchmark_symbol': form.get('benchmark_symbol'),
        'start_date_override': form.get('start_date_override'),
        'is_active': (str(form.get('is_active', '1')) in ('1','true','True','on')),
    }
    # 唯一性约束：若重复，返回 409
    try:
        res = svc.upsert_tracked_instruments([payload_item])
    except Exception as e:
        if 'UNIQUE' in str(e).upper():
            return jsonify({'success': False, 'message': 'symbol already exists'}), 409
        raise
    return jsonify({'success': True, 'data': res})


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
