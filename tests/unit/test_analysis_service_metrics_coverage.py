#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any, Optional, Tuple

from services.analysis_service import AnalysisService


class _FakeDb:
    def execute_query(self, query: str, params: Optional[Tuple[Any, ...]] = None, fetch_one: bool = False, fetch_all: bool = True):
        q = " ".join(query.split())
        # 主查询：返回一笔已平仓交易
        if q.startswith("SELECT t.*, s.name as strategy_name FROM trades t"):
            row = {
                'id': 1,
                'strategy_id': 1,
                'strategy_name': 'X',
                'symbol_code': 'AAA',
                'symbol_name': '标的A',
                'open_date': '2024-01-01',
                'status': 'closed',
                'total_buy_amount': 1000.0,
                'holding_days': 5,
            }
            return row if fetch_one else [row]

        # 手续费聚合
        if "SELECT COALESCE(SUM(transaction_fee), 0) as total_fees FROM trade_details" in q:
            return {'total_fees': 10.0} if fetch_one else [{'total_fees': 10.0}]

        # 买入聚合
        if "transaction_type='buy'" in q and "SUM(price*quantity)" in q:
            row = {'buy_gross': 1000.0, 'buy_qty': 100.0}
            return row if fetch_one else [row]

        # 卖出聚合
        if "transaction_type='sell'" in q and "SUM(price*quantity)" in q:
            row = {'sell_gross': 1200.0, 'sell_qty': 100.0, 'sell_fees': 10.0}
            return row if fetch_one else [row]

        # 默认空
        return None if fetch_one else []


def test_calculate_strategy_score_closed_trade_path():
    svc = AnalysisService(_FakeDb())
    score = svc.calculate_strategy_score()
    assert 'stats' in score
    stats = score['stats']
    # 一笔交易
    assert stats['total_trades'] == 1
    # 毛利=1200-1000=200；净利≈190；
    assert stats['total_gross_return'] > 0
    assert stats['total_net_return'] > 0
    assert stats['avg_return_per_trade'] > 0


