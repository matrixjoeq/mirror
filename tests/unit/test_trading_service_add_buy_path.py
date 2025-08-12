#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from decimal import Decimal
from typing import Any, Optional, Tuple

from services.trading_service import TradingService


class _FakeCursor:
    def __init__(self):
        self._lastrowid = 42
        self._select_mode = None

    @property
    def lastrowid(self):
        return self._lastrowid

    def execute(self, query: str, params: Tuple[Any, ...] = ()):  # noqa: D401
        q = " ".join(query.split())
        # 选择不同语句的返回模式
        if q.startswith("SELECT id FROM trades WHERE strategy_id = ? AND symbol_code = ? AND status = 'open'"):
            # 不存在开放交易
            self._select_mode = 'open_trade'
        elif q.startswith("SELECT * FROM trades WHERE id = ?"):
            # 返回新创建的 trade 基础数据供更新
            self._select_mode = 'trade_by_id'
        else:
            self._select_mode = None

    def fetchone(self):
        if self._select_mode == 'open_trade':
            return None
        if self._select_mode == 'trade_by_id':
            return {
                'id': 42,
                'total_buy_amount': 0.0,
                'total_buy_quantity': 0,
                'remaining_quantity': 0,
                'open_date': '2024-01-01',
            }
        return None


class _FakeConn:
    def __init__(self):
        self._cursor = _FakeCursor()

    def cursor(self):
        return self._cursor

    def commit(self):
        return True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeDb:
    def __init__(self):
        self._strategies = [{'id': 1, 'name': 'Alpha', 'description': '', 'is_active': 1, 'created_at': '2024-01-01', 'updated_at': '2024-01-01'}]

    def get_connection(self):
        return _FakeConn()

    def execute_query(self, query: str, params: Optional[Tuple[Any, ...]] = None, fetch_one: bool = False, fetch_all: bool = True):
        q = " ".join(query.split())
        # StrategyService.get_all_strategies 会查询 strategies
        if "FROM strategies" in q and "WHERE" not in q:
            return self._strategies
        return None if fetch_one else []


def test_add_buy_transaction_success_creates_new_trade_and_detail():
    svc = TradingService(_FakeDb())
    ok, res = svc.add_buy_transaction(
        strategy='Alpha',
        symbol_code='AAA',
        symbol_name='标的A',
        price=Decimal('10'),
        quantity=100,
        transaction_date='2024-01-01',
        transaction_fee=Decimal('1'),
        buy_reason='test'
    )
    assert ok is True
    assert isinstance(res, int) or isinstance(res, float)


