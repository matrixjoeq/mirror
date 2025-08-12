#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TradeRepository：封装 trades 与 trade_details 的读取查询，隔离 SQL。
遵循依赖倒置，服务面向接口/仓储而非直接SQL。
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal

from .database_service import DatabaseService


class TradeRepository:
    def __init__(self, db: Optional[DatabaseService] = None):
        self.db = db or DatabaseService()

    def fetch_trades(self, status: Optional[str], strategy_id: Optional[int], include_deleted: bool,
                     order_by: str, limit: Optional[int]) -> List[Dict[str, Any]]:
        query = '''
            SELECT t.*, s.name as strategy_name
            FROM trades t
            LEFT JOIN strategies s ON t.strategy_id = s.id
        '''
        conditions = []
        params: List[Any] = []
        if not include_deleted:
            conditions.append("t.is_deleted = 0")
        if status:
            conditions.append("t.status = ?")
            params.append(status)
        if strategy_id:
            conditions.append("t.strategy_id = ?")
            params.append(strategy_id)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        # whitelist columns for ordering
        ob = (order_by or '').strip()
        safe_order_by = 't.created_at DESC'
        if ob.startswith('t.') or ob.startswith('s.'):
            safe_order_by = ob
        query += f" ORDER BY {safe_order_by}"
        if limit is not None and isinstance(limit, int) and limit > 0:
            query += f" LIMIT {limit}"
        rows = self.db.execute_query(query, tuple(params))
        return [dict(r) for r in rows]

    def aggregate_trade_details(self, trade_id: int, include_deleted: bool) -> Dict[str, Decimal]:
        sql = (
            """
            SELECT 
              COALESCE(SUM(CASE WHEN transaction_type='buy' THEN price*quantity END),0) AS gross_buy,
              COALESCE(SUM(CASE WHEN transaction_type='buy' THEN transaction_fee END),0) AS buy_fees,
              COALESCE(SUM(CASE WHEN transaction_type='sell' THEN price*quantity END),0) AS gross_sell,
              COALESCE(SUM(CASE WHEN transaction_type='sell' THEN transaction_fee END),0) AS sell_fees,
              COALESCE(SUM(CASE WHEN transaction_type='sell' THEN quantity END),0) AS sold_qty,
              COALESCE(SUM(CASE WHEN transaction_type='buy' THEN quantity END),0) AS buy_qty
            FROM trade_details WHERE trade_id = ?
            """ + (" AND is_deleted = 0" if not include_deleted else "")
        )
        row = self.db.execute_query(sql, (trade_id,), fetch_one=True)
        def to_dec(k: str) -> Decimal:
            return Decimal(str(row[k])) if row and row.get(k) is not None else Decimal('0')
        return {
            'gross_buy': to_dec('gross_buy'),
            'buy_fees': to_dec('buy_fees'),
            'gross_sell': to_dec('gross_sell'),
            'sell_fees': to_dec('sell_fees'),
            'sold_qty': to_dec('sold_qty'),
            'buy_qty': to_dec('buy_qty'),
        }


