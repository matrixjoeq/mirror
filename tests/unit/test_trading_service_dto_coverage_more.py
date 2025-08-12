#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any, Optional, Tuple
from decimal import Decimal

from services.trading_service import TradingService


class _FakeDb:
    def __init__(self):
        self._calls = []

    def execute_query(self, query: str, params: Optional[Tuple[Any, ...]] = None, fetch_one: bool = False, fetch_all: bool = True):
        q = " ".join(query.split())  # normalize spaces
        self._calls.append((q, params, fetch_one))

        # compute_buy_detail_remaining_map: return full details list
        if q.startswith("SELECT * FROM trade_details WHERE trade_id = ? AND is_deleted = 0 ORDER BY"):
            return [
                {'id': 1, 'trade_id': 99, 'transaction_type': 'buy', 'quantity': 100, 'price': 10, 'transaction_fee': 1,
                 'transaction_date': '2024-01-01', 'created_at': '2024-01-01'},
                {'id': 2, 'trade_id': 99, 'transaction_type': 'buy', 'quantity': 50, 'price': 12, 'transaction_fee': 1,
                 'transaction_date': '2024-01-02', 'created_at': '2024-01-02'},
                {'id': 3, 'trade_id': 99, 'transaction_type': 'sell', 'quantity': 80, 'price': 11, 'transaction_fee': 2,
                 'transaction_date': '2024-01-03', 'created_at': '2024-01-03'},
                {'id': 4, 'trade_id': 99, 'transaction_type': 'sell', 'quantity': 30, 'price': 13, 'transaction_fee': 2,
                 'transaction_date': '2024-01-04', 'created_at': '2024-01-04'},
            ]

        # get_trade_overview_metrics: return aggregated sums row
        if q.startswith("SELECT COALESCE(SUM(CASE WHEN transaction_type='buy' THEN price*quantity END)"):
            # gross_buy = 100*10 + 50*12 = 1600
            # buy_fees = 1 + 1 = 2
            # gross_sell = 80*11 + 30*13 = 880 + 390 = 1270
            # sell_fees = 2 + 2 = 4
            # sold_qty = 110
            # buy_qty = 150
            row = {
                'gross_buy': 1600.0,
                'buy_fees': 2.0,
                'gross_sell': 1270.0,
                'sell_fees': 4.0,
                'sold_qty': 110.0,
                'buy_qty': 150.0,
            }
            return row if fetch_one else [row]

        # Fallback: empty results
        return None if fetch_one else []


def test_compute_buy_detail_remaining_map_fifo():
    svc = TradingService(_FakeDb())
    remap = svc.compute_buy_detail_remaining_map(trade_id=99)
    # 买入100+50，卖出80+30=110 ⇒ 第一笔剩余20，第二笔剩余20
    assert remap.get(1) == 20
    assert remap.get(2) == 20


def test_get_trade_overview_metrics_calculation():
    svc = TradingService(_FakeDb())
    ov = svc.get_trade_overview_metrics(trade_id=99)
    # 依据假数据进行断言
    # 平均买入不含费 = 1600 / 150 = 10.666...
    # 已卖出买入成本 = 10.666... * 110 = 1173.333...
    # 毛利 = 1270 - 1173.333... ≈ 96.6667
    # 分摊买入费 = 2 * (110/150) = 1.4666...
    # 净利 = 96.6667 - 4 - 1.4666... ≈ 91.2
    assert isinstance(ov, dict)
    assert ov['buy_gross'] == 1600.0
    assert ov['sell_gross'] == 1270.0
    assert ov['buy_fees'] == 2.0
    assert ov['sell_fees'] == 4.0
    assert ov['total_net_profit'] > 0
    assert ov['total_profit_loss'] > 0


