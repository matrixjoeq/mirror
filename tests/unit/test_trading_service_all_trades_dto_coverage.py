#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal

from services.trading_service import TradingService


class _FakeRepo:
    def __init__(self):
        self.calls: List[Tuple[str, tuple]] = []

    def fetch_trades(self, status: Optional[str], strategy_id: Optional[int], include_deleted: bool,
                      order_by: str, limit: Optional[int]) -> List[Dict[str, Any]]:
        # 返回一条开放交易记录（含必要字段）
        return [{
            'id': 101,
            'strategy_id': 1,
            'strategy_name': '测试策略',
            'symbol_code': 'TST',
            'symbol_name': '测试标的',
            'status': 'open',
            'remaining_quantity': 50,
            'holding_days': 5,
            'total_buy_amount': 0,
            'total_sell_amount': 0,
            'total_profit_loss': 0,
            'total_profit_loss_pct': 0,
        }]

    def aggregate_trade_details(self, trade_id: int, include_deleted: bool = False) -> Dict[str, Any]:
        # 模拟有买入 100 股（不含费 1000，买入费 2），已卖出 50 股（不含费 600，卖出费 1）
        return {
            'gross_buy': 1000.0,
            'buy_fees': 2.0,
            'gross_sell': 600.0,
            'sell_fees': 1.0,
            'sold_qty': 50.0,
            'buy_qty': 100.0,
        }


class _FakeDb:
    def execute_query(self, query: str, params: Optional[Tuple[Any, ...]] = None, fetch_one: bool = False, fetch_all: bool = True):
        # 仅用于 get_trade_details 的查询模拟
        q = " ".join(query.split())
        if q.startswith("SELECT * FROM trade_details WHERE trade_id = ?"):
            return [
                {
                    'id': 1, 'trade_id': 101, 'transaction_type': 'buy', 'price': 10, 'quantity': 100,
                    'amount': 1002, 'transaction_date': '2024-01-01', 'transaction_fee': 2,
                    'buy_reason': '', 'sell_reason': '', 'profit_loss': 0, 'profit_loss_pct': 0,
                    'created_at': '2024-01-01', 'is_deleted': 0, 'delete_date': None, 'delete_reason': '', 'operator_note': ''
                },
                {
                    'id': 2, 'trade_id': 101, 'transaction_type': 'sell', 'price': 12, 'quantity': 50,
                    'amount': 599, 'transaction_date': '2024-01-10', 'transaction_fee': 1,
                    'buy_reason': '', 'sell_reason': '', 'profit_loss': 100, 'profit_loss_pct': 10,
                    'created_at': '2024-01-10', 'is_deleted': 0, 'delete_date': None, 'delete_reason': '', 'operator_note': ''
                },
            ]
        # 其余查询返回空或哑值
        if fetch_one:
            return None
        return []


def test_get_all_trades_return_dto_with_metrics():
    svc = TradingService(_FakeDb())
    # 注入仓储假对象，驱动聚合路径
    svc.trade_repo = _FakeRepo()
    dtos = svc.get_all_trades(return_dto=True)
    assert isinstance(dtos, list) and len(dtos) == 1
    dto = dtos[0]
    # 校验关键派生字段已填充
    assert dto.total_gross_profit >= 0
    assert dto.total_net_profit >= 0
    assert dto.total_fees >= 0
    assert dto.total_fee_ratio_pct >= 0


def test_get_trade_details_return_dto():
    svc = TradingService(_FakeDb())
    details = svc.get_trade_details(101, return_dto=True)
    assert isinstance(details, list) and len(details) == 2
    assert hasattr(details[0], 'transaction_type')


