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
                     order_by: str, limit: Optional[int], offset: Optional[int] = None,
                     symbols: Optional[List[str]] = None,
                     symbol_names: Optional[List[str]] = None,
                     date_from: Optional[str] = None,
                     date_to: Optional[str] = None) -> List[Dict[str, Any]]:
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
        # 按标的代码过滤（支持多个代码）
        if symbols:
            symbols_clean = [str(s).strip().upper() for s in symbols if str(s).strip()]
            if symbols_clean:
                placeholders = ",".join(["?"] * len(symbols_clean))
                conditions.append(f"UPPER(t.symbol_code) IN ({placeholders})")
                params.extend(symbols_clean)
        if symbol_names:
            names_clean = [str(s).strip().upper() for s in symbol_names if str(s).strip()]
            if names_clean:
                placeholders = ",".join(["?"] * len(names_clean))
                conditions.append(f"UPPER(t.symbol_name) IN ({placeholders})")
                params.extend(names_clean)
        # 日期区间过滤（开仓或平仓在区间内）
        df = (date_from or '').strip()
        dt = (date_to or '').strip()
        if df and dt:
            conditions.append("(t.open_date BETWEEN ? AND ? OR t.close_date BETWEEN ? AND ?)")
            params.extend([df, dt, df, dt])
        elif df:
            conditions.append("(t.open_date >= ? OR (t.close_date IS NOT NULL AND t.close_date >= ?))")
            params.extend([df, df])
        elif dt:
            conditions.append("(t.open_date <= ? OR (t.close_date IS NOT NULL AND t.close_date <= ?))")
            params.extend([dt, dt])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        # whitelist columns for ordering
        ob = (order_by or '').strip()
        safe_order_by = 't.created_at DESC'
        # 简单白名单校验：仅允许以 t./s. 开头，并且仅包含一个空格分隔 ASC/DESC
        if (ob.startswith('t.') or ob.startswith('s.')) and (';' not in ob):
            safe_order_by = ob
        query += f" ORDER BY {safe_order_by}"
        if limit is not None and isinstance(limit, int) and limit > 0:
            # LIMIT 和 OFFSET 仅接受非负整数，来源已在上游校验
            query += f" LIMIT {int(limit)}"
            if offset is not None and isinstance(offset, int) and offset >= 0:
                query += f" OFFSET {int(offset)}"
        rows = self.db.execute_query(query, tuple(params))
        return [dict(r) for r in rows]

    def count_trades(self, status: Optional[str], strategy_id: Optional[int], include_deleted: bool,
                     symbols: Optional[List[str]] = None,
                     symbol_names: Optional[List[str]] = None,
                     date_from: Optional[str] = None,
                     date_to: Optional[str] = None) -> int:
        """统计满足条件的交易总数（用于分页）。"""
        query = '''
            SELECT COUNT(*) AS cnt
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
        if symbols:
            symbols_clean = [str(s).strip().upper() for s in symbols if str(s).strip()]
            if symbols_clean:
                placeholders = ",".join(["?"] * len(symbols_clean))
                conditions.append(f"UPPER(t.symbol_code) IN ({placeholders})")
                params.extend(symbols_clean)
        if symbol_names:
            names_clean = [str(s).strip().upper() for s in symbol_names if str(s).strip()]
            if names_clean:
                placeholders = ",".join(["?"] * len(names_clean))
                conditions.append(f"UPPER(t.symbol_name) IN ({placeholders})")
                params.extend(names_clean)
        # 日期区间过滤（开仓或平仓在区间内）
        df = (date_from or '').strip()
        dt = (date_to or '').strip()
        if df and dt:
            conditions.append("(t.open_date BETWEEN ? AND ? OR t.close_date BETWEEN ? AND ?)")
            params.extend([df, dt, df, dt])
        elif df:
            conditions.append("(t.open_date >= ? OR (t.close_date IS NOT NULL AND t.close_date >= ?))")
            params.extend([df, df])
        elif dt:
            conditions.append("(t.open_date <= ? OR (t.close_date IS NOT NULL AND t.close_date <= ?))")
            params.extend([dt, dt])

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        row = self.db.execute_query(query, tuple(params), fetch_one=True)
        try:
            return int(row['cnt']) if row and 'cnt' in row.keys() else 0
        except Exception:
            return int(row[0]) if row else 0

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


