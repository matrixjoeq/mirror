#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易相关路由
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app
from decimal import Decimal

from services import TradingService, StrategyService
from services.mappers import dto_list_to_dicts
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
        status = request.args.get('status', 'all')
        strategy_arg = request.args.get('strategy', 'all')
        # 分页参数
        page_arg = request.args.get('page', '1')
        page_size_arg = request.args.get('page_size', '25')

        # 归一化筛选值供服务层使用（'all' 等价于不筛选）
        status_filter = None if not status or status == 'all' else status
        strategy_filter = None
        if strategy_arg and strategy_arg != 'all':
            try:
                strategy_filter = int(strategy_arg)
            except ValueError:
                strategy_filter = strategy_arg

        # 解析分页参数（容错）
        try:
            page = int(page_arg)
        except Exception:
            page = 1
        try:
            page_size = int(page_size_arg)
        except Exception:
            page_size = 25
        if page < 1:
            page = 1
        if page_size not in (25, 50, 100):
            page_size = 25

        # 表头排序参数
        sort_key = request.args.get('sort', 'open_date')
        sort_dir = request.args.get('dir', 'desc').lower()
        if sort_dir not in ('asc', 'desc'):
            sort_dir = 'desc'
        # 允许排序的列（白名单），映射到安全的 SQL 列
        allowed_sort_columns = {
            'id': 't.id',
            'strategy_name': 's.name',
            'symbol_code': 't.symbol_code',
            'symbol_name': 't.symbol_name',
            'open_date': 't.open_date',
            'close_date': 't.close_date',
            'status': 't.status',
            'remaining_quantity': 't.remaining_quantity',
            'total_buy_amount': 't.total_buy_amount',
            'total_sell_amount': 't.total_sell_amount',
            'total_net_profit': 't.total_net_profit',
            'total_net_profit_pct': 't.total_net_profit_pct',
            'total_buy_fees': 't.total_buy_fees',
            'total_sell_fees': 't.total_sell_fees',
            'total_profit_loss': 't.total_profit_loss',
            'total_profit_loss_pct': 't.total_profit_loss_pct',
            'total_fees': 't.total_fees',
            'total_fee_ratio_pct': 't.total_fee_ratio_pct',
            'holding_days': 't.holding_days',
        }
        order_col = allowed_sort_columns.get(sort_key, 't.open_date')
        order_by = f"{order_col} {'DESC' if sort_dir == 'desc' else 'ASC'}"

        # 标的代码过滤（支持多个，逗号/空格分隔）
        symbols_raw = request.args.get('symbols', '').strip()
        symbols_list = []
        if symbols_raw:
            # 支持逗号、空白分隔，统一去重与标准化大小写
            tmp = [p for chunk in symbols_raw.replace('，', ',').split(',') for p in chunk.split()] if symbols_raw else []
            symbols_list = list({s.strip().upper() for s in tmp if s.strip()})

        # 标的名称过滤（支持多个，逗号/空格分隔）
        names_raw = request.args.get('names', '').strip()
        names_list = []
        if names_raw:
            tmp = [p for chunk in names_raw.replace('，', ',').split(',') for p in chunk.split()] if names_raw else []
            names_list = list({s.strip().upper() for s in tmp if s.strip()})

        # 日期区间过滤参数（YYYY-MM-DD）
        date_from = request.args.get('date_from', '').strip() or None
        date_to = request.args.get('date_to', '').strip() or None

        # 获取交易数据（分页）
        trades_dto, total_count = trading_service.get_trades_paginated(
            status=status_filter,
            strategy=strategy_filter,
            order_by=order_by,
            page=page,
            page_size=page_size,
            return_dto=True,
            symbols=symbols_list,
            symbol_names=names_list,
            date_from=date_from,
            date_to=date_to,
        )
        strategies_list_raw = strategy_service.get_all_strategies(return_dto=True)

        # 路由层对 DTO 做轻度字典化，便于模板渲染
        all_trades = dto_list_to_dicts(trades_dto)
        strategies_list = dto_list_to_dicts(strategies_list_raw)

        # 分页元信息
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

        return render_template('trades.html',
                             trades=all_trades,
                             strategies=strategies_list,
                             current_status=status,
                             current_strategy=str(strategy_arg),
                             sort_key=sort_key,
                             sort_dir=sort_dir,
                             symbols_query=symbols_raw,
                             names_query=names_raw,
                             date_from=date_from or '',
                             date_to=date_to or '',
                             page=page,
                             page_size=page_size,
                             total_count=total_count,
                             total_pages=total_pages)

    except Exception as e:
        current_app.logger.error(f"交易列表加载失败: {str(e)}")
        return render_template('trades.html', trades=[], strategies=[])


@trading_bp.route('/add_buy', methods=['GET', 'POST'])
def add_buy():
    """添加买入交易"""
    if request.method == 'GET':
        try:
            strategy_service = StrategyService(current_app.db_service)
            strategies = strategy_service.get_all_strategies()

            # 获取URL参数中的策略ID
            default_strategy_id = request.args.get('strategy')
            default_strategy = None

            # 如果URL中有策略参数，验证策略是否存在
            if default_strategy_id:
                try:
                    strategy_id = int(default_strategy_id)
                    # 验证策略是否存在
                    strategy_obj = strategy_service.get_strategy_by_id(strategy_id)
                    if strategy_obj:
                        default_strategy = strategy_id
                except ValueError:
                    pass  # 忽略无效的策略ID

            return render_template('add_buy.html',
                                 strategies_data=strategies,
                                 default_strategy=default_strategy)
        except Exception as e:
            current_app.logger.error(f"买入页面加载失败: {str(e)}")
            return render_template('add_buy.html', strategies_data=[], default_strategy=None)

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
                strategy_service = StrategyService(current_app.db_service)
                strategies = strategy_service.get_all_strategies()
                return render_template('add_buy.html',
                                     strategies_data=strategies,
                                     error=result)

        except Exception as e:
            current_app.logger.error(f"添加买入交易失败: {str(e)}")
            strategy_service = StrategyService(current_app.db_service)
            strategies = strategy_service.get_all_strategies()
            return render_template('add_buy.html',
                                 strategies_data=strategies,
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

            # 计算不含费用的平均买入价供前端盈亏预览
            db = current_app.db_service
            row = db.execute_query(
                """
                SELECT COALESCE(SUM(price * quantity), 0) AS gross_buy,
                       COALESCE(SUM(quantity), 0) AS qty
                FROM trade_details
                WHERE trade_id = ? AND transaction_type = 'buy' AND is_deleted = 0
                """,
                (trade_id,),
                fetch_one=True,
            )
            gross_buy = row['gross_buy'] if row else 0
            qty = row['qty'] if row else 0
            avg_buy_price_ex_fee = float(gross_buy) / float(qty) if qty else 0.0

            return render_template('add_sell.html', trade=trade, avg_buy_price_ex_fee=avg_buy_price_ex_fee)

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

        details_raw = trading_service.get_trade_details(trade_id, return_dto=True)
        modifications = trading_service.get_trade_modifications(trade_id)
        details = dto_list_to_dicts(details_raw)

        # 计算每个买入明细的剩余可卖份额（FIFO视角）
        remaining_map = trading_service.compute_buy_detail_remaining_map(trade_id)
        # 将剩余份额与可卖状态合并到 details 中，便于模板禁用按钮
        details_with_remaining = []
        for d in details:
            if d['transaction_type'] == 'buy':
                rem = int(remaining_map.get(d['id'], d['quantity']))
                d['remaining_for_quick'] = rem
                d['can_quick_sell'] = (trade['status'] == 'open' and trade['remaining_quantity'] > 0 and rem > 0)
            else:
                d['remaining_for_quick'] = 0
                d['can_quick_sell'] = False
            details_with_remaining.append(d)

        # 使用统一服务接口，保证与列表/首页一致
        overview_metrics = trading_service.get_trade_overview_metrics(trade_id)
        return render_template('trade_details.html',
                             trade=trade,
                             details=details_with_remaining,
                             modifications=modifications,
                             overview=overview_metrics)

    except Exception as e:
        current_app.logger.error(f"交易详情加载失败: {str(e)}")
        return redirect(url_for('trading.trades'))


@trading_bp.route('/edit_trade/<int:trade_id>', methods=['GET', 'POST'])
def edit_trade(trade_id):
    """编辑交易"""
    try:
        trading_service = TradingService(current_app.db_service)
        strategy_service = StrategyService(current_app.db_service)

        # 统一获取交易对象，并检查删除状态
        trade = trading_service.get_trade_by_id(trade_id, include_deleted=True)
        if not trade:
            return redirect(url_for('trading.trades'))

        if trade.get('is_deleted'):
            # 在这里可以增加 flash 消息
            return redirect(url_for('trading.trades'))

        if request.method == 'GET':
            strategies_raw = strategy_service.get_all_strategies(return_dto=True)
            strategies = dto_list_to_dicts(strategies_raw)
            details = dto_list_to_dicts(trading_service.get_trade_details(trade_id, return_dto=True))

            # 为模板提供便于显示的策略字典与列表
            strategies_dict = {s['id']: s['name'] for s in strategies}
            return render_template(
                'edit_trade.html',
                trade=trade,
                details=details,
                strategies_data=strategies,
                strategies_dict=strategies_dict,
            )

        elif request.method == 'POST':
            # 处理表单提交
            updates = {
                'strategy_id': request.form.get('strategy_id', type=int),
                'symbol_code': request.form.get('symbol_code'),
                'symbol_name': request.form.get('symbol_name'),
                'open_date': request.form.get('open_date'),
            }
            # 过滤掉 None 值，防止意外清空
            updates = {k: v for k, v in updates.items() if v is not None}

            modification_reason = request.form.get('modification_reason', '用户界面编辑')

            success, message = trading_service.edit_trade(
                trade_id=trade_id,
                updates=updates,
                modification_reason=modification_reason
            )

            if success:
                return redirect(url_for('trading.trade_details', trade_id=trade_id))
            else:
                # 为空提交或其他错误时，保持与历史行为一致：重定向回编辑页
                return redirect(url_for('trading.edit_trade', trade_id=trade_id))

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
    trading_service = TradingService(current_app.db_service)

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
        trading_service = TradingService(current_app.db_service)
        strategy_service = StrategyService(current_app.db_service)

        deleted_trades_list = trading_service.get_deleted_trades()
        strategies = strategy_service.get_all_strategies()

        # 创建策略ID到名称的映射
        strategy_map = {strategy['id']: strategy['name'] for strategy in strategies}

        return render_template('deleted_trades.html', trades=deleted_trades_list, strategies=strategy_map)

    except Exception as e:
        current_app.logger.error(f"已删除交易列表加载失败: {str(e)}")
        return render_template('deleted_trades.html', trades=[], strategies={})


@trading_bp.route('/restore_trade/<int:trade_id>', methods=['POST'])
@handle_errors
def restore_trade(trade_id):
    """恢复已删除的交易"""
    trading_service = TradingService(current_app.db_service)

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
    trading_service = TradingService(current_app.db_service)

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


@trading_bp.route('/batch_delete_trades', methods=['POST'])
@handle_errors
def batch_delete_trades():
    """批量软删除交易"""
    trading_service = TradingService(current_app.db_service)

    trade_ids = request.form.getlist('trade_ids[]')
    confirmation_code = request.form.get('confirmation_code')
    delete_reason = request.form.get('delete_reason', '')
    operator_note = request.form.get('operator_note', '')

    if not trade_ids:
        return jsonify({'success': False, 'message': '未选择任何交易'}), 400
    if not confirmation_code:
        return jsonify({'success': False, 'message': '请提供确认码'}), 400

    success_count = 0
    for tid in trade_ids:
        try:
            trade_id = int(tid)
        except Exception:
            continue
        ok = trading_service.soft_delete_trade(
            trade_id=trade_id,
            confirmation_code=confirmation_code,
            delete_reason=delete_reason,
            operator_note=operator_note,
        )
        if ok:
            success_count += 1

    if success_count == len(trade_ids):
        return jsonify({'success': True, 'message': f'成功删除 {success_count} 笔交易'})
    elif success_count == 0:
        return jsonify({'success': False, 'message': '删除失败，请重试'}), 500
    else:
        return jsonify({'success': True, 'message': f'部分成功：已删除 {success_count}/{len(trade_ids)} 笔交易'})


@trading_bp.route('/batch_restore_trades', methods=['POST'])
@handle_errors
def batch_restore_trades():
    """批量恢复交易"""
    trading_service = TradingService(current_app.db_service)

    trade_ids = request.form.getlist('trade_ids[]')
    confirmation_code = request.form.get('confirmation_code')
    operator_note = request.form.get('operator_note', '')

    if not trade_ids:
        return jsonify({'success': False, 'message': '未选择任何交易'}), 400
    if not confirmation_code:
        return jsonify({'success': False, 'message': '请提供确认码'}), 400

    success_count = 0
    for tid in trade_ids:
        try:
            trade_id = int(tid)
        except Exception:
            continue
        ok = trading_service.restore_trade(
            trade_id=trade_id,
            confirmation_code=confirmation_code,
            operator_note=operator_note,
        )
        if ok:
            success_count += 1

    if success_count == len(trade_ids):
        return jsonify({'success': True, 'message': f'成功恢复 {success_count} 笔交易'})
    elif success_count == 0:
        return jsonify({'success': False, 'message': '恢复失败，请重试'}), 500
    else:
        return jsonify({'success': True, 'message': f'部分成功：已恢复 {success_count}/{len(trade_ids)} 笔交易'})


@trading_bp.route('/batch_permanently_delete_trades', methods=['POST'])
@handle_errors
def batch_permanently_delete_trades():
    """批量永久删除交易"""
    trading_service = TradingService(current_app.db_service)

    trade_ids = request.form.getlist('trade_ids[]')
    confirmation_code = request.form.get('confirmation_code')
    confirmation_text = request.form.get('confirmation_text')
    delete_reason = request.form.get('delete_reason', '')
    operator_note = request.form.get('operator_note', '')

    if not trade_ids:
        return jsonify({'success': False, 'message': '未选择任何交易'}), 400
    if not confirmation_code or not confirmation_text:
        return jsonify({'success': False, 'message': '请提供确认码和确认文本'}), 400

    success_count = 0
    for tid in trade_ids:
        try:
            trade_id = int(tid)
        except Exception:
            continue
        ok = trading_service.permanently_delete_trade(
            trade_id=trade_id,
            confirmation_code=confirmation_code,
            confirmation_text=confirmation_text,
            delete_reason=delete_reason,
            operator_note=operator_note,
        )
        if ok:
            success_count += 1

    if success_count == len(trade_ids):
        return jsonify({'success': True, 'message': f'成功彻底删除 {success_count} 笔交易'})
    elif success_count == 0:
        return jsonify({'success': False, 'message': '彻底删除失败，请重试'}), 500
    else:
        return jsonify({'success': True, 'message': f'部分成功：已彻底删除 {success_count}/{len(trade_ids)} 笔交易'})
