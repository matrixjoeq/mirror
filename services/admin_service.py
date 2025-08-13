#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库维护与一致性校验服务：
- 诊断交易主表与明细表之间的数据不一致
- 基于明细数据（source of truth）进行自动校准
- 提供原始行级数据更新能力（受控字段）
"""

from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime

from .database_service import DatabaseService
from .trading_service import TradingService


class DatabaseMaintenanceService:
    def __init__(self, db: DatabaseService, trading_service: TradingService):
        self.db = db
        self.trading_service = trading_service

    # --------------------- 校验与诊断 ---------------------
    def validate_database(self, trade_id: Optional[int] = None) -> Dict[str, Any]:
        """校验 trades 与 trade_details 的一致性与完整性。

        返回结构：{
          'summary': {...},
          'trade_issues': [ {trade_id, field, current, expected} ... ],
          'detail_issues': [ {detail_id, issue, current, expected} ... ]
        }
        """
        trade_issues: List[Dict[str, Any]] = []
        detail_issues: List[Dict[str, Any]] = []

        # 选择交易范围
        if trade_id is None:
            rows = self.db.execute_query(
                "SELECT id FROM trades WHERE is_deleted = 0 ORDER BY id"
            )
            trade_ids = [int(r['id']) for r in rows]
        else:
            trade_ids = [int(trade_id)]

        for tid in trade_ids:
            # 主表快照
            trade = self.db.execute_query(
                "SELECT * FROM trades WHERE id = ?", (tid,), fetch_one=True
            )
            if not trade:
                continue
            # 将 sqlite3.Row 访问包装为兼容 dict 的获取
            def _row_get(row, key, default=None):
                try:
                    return row[key]
                except Exception:
                    return default

            # 明细聚合（不含费成交与费用分离）
            sums = self.db.execute_query(
                """
                SELECT
                  COALESCE(SUM(CASE WHEN transaction_type='buy' THEN price*quantity END),0) AS gross_buy,
                  COALESCE(SUM(CASE WHEN transaction_type='buy' THEN transaction_fee END),0) AS buy_fees,
                  COALESCE(SUM(CASE WHEN transaction_type='sell' THEN price*quantity END),0) AS gross_sell,
                  COALESCE(SUM(CASE WHEN transaction_type='sell' THEN transaction_fee END),0) AS sell_fees,
                  COALESCE(SUM(CASE WHEN transaction_type='sell' THEN quantity END),0) AS sold_qty,
                  COALESCE(SUM(CASE WHEN transaction_type='buy' THEN quantity END),0) AS buy_qty
                FROM trade_details WHERE trade_id = ? AND is_deleted = 0
                """,
                (tid,),
                fetch_one=True,
            )

            gross_buy = Decimal(str(sums['gross_buy'])) if sums else Decimal('0')
            buy_fees = Decimal(str(sums['buy_fees'])) if sums else Decimal('0')
            gross_sell = Decimal(str(sums['gross_sell'])) if sums else Decimal('0')
            sell_fees = Decimal(str(sums['sell_fees'])) if sums else Decimal('0')
            sold_qty = Decimal(str(sums['sold_qty'])) if sums else Decimal('0')
            buy_qty = Decimal(str(sums['buy_qty'])) if sums else Decimal('0')
            remaining_qty_expected = int(buy_qty - sold_qty)

            # WAC 毛/净
            avg_buy_ex = (gross_buy / buy_qty) if buy_qty > 0 else Decimal('0')
            buy_cost_for_sold = avg_buy_ex * sold_qty
            gross_profit = gross_sell - buy_cost_for_sold
            # 分摊买入费
            buy_fee_alloc_for_sold = (buy_fees * (sold_qty / buy_qty)) if buy_qty > 0 else Decimal('0')
            net_profit = gross_profit - sell_fees - buy_fee_alloc_for_sold
            denom = buy_cost_for_sold
            net_profit_pct = float((net_profit / denom * 100) if denom > 0 else 0)
            gross_profit_pct = float((gross_profit / denom * 100) if denom > 0 else 0)

            # 主表字段期望值（与列表/详情统一：买入/卖出金额均为不含费用的成交额；费用单列）
            buy_amount_expected = float(gross_buy)
            sell_amount_expected = float(gross_sell)
            buy_qty_expected = int(buy_qty)
            sell_qty_expected = int(sold_qty)

            # 状态与收盘日期
            status_expected = 'closed' if remaining_qty_expected == 0 and sell_qty_expected > 0 else 'open'
            close_date_expected = None
            if status_expected == 'closed':
                row = self.db.execute_query(
                    "SELECT MAX(transaction_date) AS cd FROM trade_details WHERE trade_id = ? AND transaction_type='sell' AND is_deleted = 0",
                    (tid,),
                    fetch_one=True,
                )
                close_date_expected = row['cd'] if row and row['cd'] else None

            # 对比并登记问题
            def _is_number(x: Any) -> bool:
                try:
                    float(x)
                    return True
                except Exception:
                    return False

            def _round_for_field(field: str, value: Any) -> Any:
                # 金额类统一保留3位小数，比例类保留2位，数量为整数
                if value is None:
                    return None
                if field.endswith('_quantity') or field in ('remaining_quantity',):
                    try:
                        return int(value)
                    except Exception:
                        return value
                if field.endswith('_pct') or field.endswith('_ratio_pct'):
                    try:
                        return round(float(value), 2)
                    except Exception:
                        return value
                # 金额/费用/利润
                if field.startswith('total_') or field in ('total_gross_profit', 'total_net_profit'):
                    try:
                        return round(float(value), 3)
                    except Exception:
                        return value
                return value

            def _add_issue(field: str, current: Any, expected: Any):
                if (current is None and expected is None):
                    return
                # 容忍不同存储精度，按字段语义进行四舍五入后比较
                cur_n = _round_for_field(field, current)
                exp_n = _round_for_field(field, expected)
                if str(cur_n) != str(exp_n):
                    trade_issues.append({
                        'trade_id': tid,
                        'field': field,
                        'current': current,
                        'expected': expected,
                    })

            _add_issue('total_buy_amount', trade['total_buy_amount'], buy_amount_expected)
            _add_issue('total_buy_quantity', trade['total_buy_quantity'], buy_qty_expected)
            _add_issue('total_sell_amount', trade['total_sell_amount'], sell_amount_expected)
            _add_issue('total_sell_quantity', trade['total_sell_quantity'], sell_qty_expected)
            _add_issue('remaining_quantity', trade['remaining_quantity'], remaining_qty_expected)
            _add_issue('total_profit_loss', trade['total_profit_loss'], float(gross_profit))
            _add_issue('total_profit_loss_pct', trade['total_profit_loss_pct'], gross_profit_pct)
            _add_issue('total_gross_profit', _row_get(trade, 'total_gross_profit', 0), float(gross_profit))
            _add_issue('total_net_profit', _row_get(trade, 'total_net_profit', 0), float(net_profit))
            _add_issue('total_net_profit_pct', _row_get(trade, 'total_net_profit_pct', 0), net_profit_pct)
            # 费用字段：确保列表页显示非零
            _add_issue('total_buy_fees', _row_get(trade, 'total_buy_fees', 0), float(buy_fees))
            _add_issue('total_sell_fees', _row_get(trade, 'total_sell_fees', 0), float(sell_fees))
            _add_issue('total_fees', _row_get(trade, 'total_fees', 0), float(buy_fees + sell_fees))
            fee_ratio = float(((buy_fees + sell_fees) / gross_buy * 100) if gross_buy > 0 else 0)
            _add_issue('total_fee_ratio_pct', _row_get(trade, 'total_fee_ratio_pct', 0), fee_ratio)
            _add_issue('status', trade['status'], status_expected)
            _add_issue('close_date', trade['close_date'], close_date_expected)

            # 校验明细 amount 定义：
            details = self.db.execute_query(
                "SELECT id, transaction_type, price, quantity, amount, transaction_fee FROM trade_details WHERE trade_id = ? AND is_deleted = 0 ORDER BY transaction_date, created_at, id",
                (tid,)
            )
            for d in details:
                price = Decimal(str(d['price']))
                qty = Decimal(str(d['quantity']))
                fee = Decimal(str(d['transaction_fee'] or 0))
                amount = Decimal(str(d['amount']))
                if d['transaction_type'] == 'buy':
                    expect_amt = price * qty + fee
                else:
                    expect_amt = price * qty - fee
                if amount != expect_amt:
                    detail_issues.append({
                        'detail_id': int(d['id']),
                        'trade_id': tid,
                        'issue': 'amount_mismatch',
                        'current': float(amount),
                        'expected': float(expect_amt),
                    })

        return {
            'summary': {
                'trade_issue_count': len(trade_issues),
                'detail_issue_count': len(detail_issues),
            },
            'trade_issues': trade_issues,
            'detail_issues': detail_issues,
        }

    # --------------------- 自动修复 ---------------------
    def auto_fix(self, trade_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """对指定交易或全部交易进行自动校准（基于明细重算主表汇总与盈亏）。"""
        fixed: List[int] = []
        failed: List[Tuple[int, str]] = []

        if trade_ids is None:
            rows = self.db.execute_query("SELECT id FROM trades WHERE is_deleted = 0 ORDER BY id")
            trade_ids = [int(r['id']) for r in rows]

        for tid in trade_ids:
            ok, msg = self.trading_service.update_trade_record(tid, [])
            if ok:
                fixed.append(tid)
            else:
                failed.append((tid, msg))

        return {'fixed': fixed, 'failed': failed}

    # --------------------- 原始数据更新（受控） ---------------------
    def update_raw_row(self, table: str, pk_id: int, updates: Dict[str, Any]) -> Tuple[bool, str]:
        """更新原始表行（限制可编辑字段并记录修改历史）。"""
        table = table.strip().lower()
        if table not in ('trades', 'trade_details'):
            return False, '不支持的表名'

        editable_trades = {
            'strategy_id', 'symbol_code', 'symbol_name', 'open_date', 'close_date', 'status', 'trade_log', 'operator_note'
        }
        editable_details = {
            'price', 'quantity', 'transaction_fee', 'transaction_date', 'buy_reason', 'sell_reason', 'operator_note',
            # 允许修正历史 amount 字段（买入含费、卖出净额），便于校准与旧字段兼容
            'amount'
        }

        allowed = editable_trades if table == 'trades' else editable_details
        set_clauses: List[str] = []
        params: List[Any] = []
        for k, v in updates.items():
            if k in allowed:
                set_clauses.append(f"{k} = ?")
                params.append(v)

        if not set_clauses:
            return False, '没有可更新字段'

        # 记录修改历史
        try:
            if table == 'trades':
                trade_row = self.db.execute_query("SELECT * FROM trades WHERE id = ?", (pk_id,), fetch_one=True)
                if not trade_row:
                    return False, '交易不存在'
                for k, v in updates.items():
                    if k in allowed:
                        self.trading_service.record_modification(pk_id, None, 'edit_trade', k, str(trade_row[k]), str(v))
            else:
                detail_row = self.db.execute_query("SELECT * FROM trade_details WHERE id = ?", (pk_id,), fetch_one=True)
                if not detail_row:
                    return False, '交易明细不存在'
                trade_id = int(detail_row['trade_id'])
                for k, v in updates.items():
                    if k in allowed:
                        self.trading_service.record_modification(trade_id, pk_id, 'edit_detail', k, str(detail_row[k]), str(v))
        except Exception:
            pass

        # 执行更新
        query = f"UPDATE {table} SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?" if table == 'trades' \
            else f"UPDATE {table} SET {', '.join(set_clauses)} WHERE id = ?"
        params.append(pk_id)
        try:
            self.db.execute_query(query, tuple(params), fetch_all=False)
            # 若更新明细，自动触发该交易的重算
            if table == 'trade_details':
                row = self.db.execute_query("SELECT trade_id FROM trade_details WHERE id = ?", (pk_id,), fetch_one=True)
                if row:
                    self.trading_service.update_trade_record(int(row['trade_id']), [])
            return True, '更新成功'
        except Exception as e:
            return False, f'更新失败: {e}'


