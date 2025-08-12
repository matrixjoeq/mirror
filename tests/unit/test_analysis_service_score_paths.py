#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from typing import Any, Optional, Tuple

from services.analysis_service import AnalysisService


class _FakeDb:
    def __init__(self):
        # two strategies
        self._strategies = [
            {'id': 1, 'name': 'Alpha', 'description': 'd', 'is_active': 1, 'created_at': '2024-01-01', 'updated_at': '2024-01-02'},
            {'id': 2, 'name': 'Beta', 'description': 'd', 'is_active': 1, 'created_at': '2024-01-03', 'updated_at': '2024-01-04'},
        ]

    def execute_query(self, query: str, params: Optional[Tuple[Any, ...]] = None, fetch_one: bool = False, fetch_all: bool = True):
        q = " ".join(query.split())

        # StrategyService.get_all_strategies
        if q.startswith('SELECT s.*, GROUP_CONCAT(st.name) as tag_names FROM strategies s') and 'GROUP BY s.id ORDER BY s.name' in q:
            rows = []
            for s in self._strategies:
                row = dict(s)
                row['tag_names'] = None
                rows.append(row)
            return rows

        # AnalysisService.calculate_strategy_score main trades query
        if q.startswith('SELECT t.*, s.name as strategy_name FROM trades t'):
            # return 2 trades (1 closed, 1 open), both for Alpha
            rows = [
                {
                    'id': 101, 'strategy_id': 1, 'strategy_name': 'Alpha',
                    'symbol_code': 'AAA', 'symbol_name': '标的A', 'open_date': '2024-01-01',
                    'status': 'closed', 'total_buy_amount': 1000.0, 'holding_days': 5,
                    'total_profit_loss': 200.0,
                },
                {
                    'id': 102, 'strategy_id': 1, 'strategy_name': 'Alpha',
                    'symbol_code': 'BBB', 'symbol_name': '标的B', 'open_date': '2024-01-05',
                    'status': 'open', 'total_buy_amount': 500.0, 'holding_days': 2,
                },
            ]
            return rows

        # Fees sum for a trade
        if "SELECT COALESCE(SUM(transaction_fee), 0) as total_fees FROM trade_details" in q:
            return {'total_fees': 10.0} if fetch_one else [{'total_fees': 10.0}]

        # Buy agg for a trade
        if "transaction_type='buy'" in q and "SUM(price*quantity)" in q:
            return {'buy_gross': 1000.0, 'buy_qty': 100.0}

        # Sell agg for a trade
        if "transaction_type='sell'" in q and "SUM(price*quantity)" in q:
            return {'sell_gross': 1200.0, 'sell_qty': 100.0, 'sell_fees': 10.0}

        # get_all_symbols
        if q.startswith('SELECT symbol_code, symbol_name, COUNT(*) as trade_count FROM trades'):
            return [
                {'symbol_code': 'AAA', 'symbol_name': '标的A', 'trade_count': 1},
                {'symbol_code': 'BBB', 'symbol_name': '标的B', 'trade_count': 1},
            ]

        # time periods
        if q.startswith("SELECT DISTINCT strftime('%Y', open_date) as period"):
            return [{'period': '2024'}]
        if q.startswith("SELECT DISTINCT strftime('%Y-%m', open_date) as period"):
            return [{'period': '2024-01'}]
        if '||' in q and 'CASE' in q and 'END as period' in q:
            return [{'period': '2024-Q1'}]

        # symbol list for strategy
        if q.startswith('SELECT DISTINCT symbol_code, symbol_name FROM trades'):
            return [{'symbol_code': 'AAA', 'symbol_name': '标的A'}]

        return None if fetch_one else []


class TestAnalysisServiceScorePaths(unittest.TestCase):
    def test_get_strategy_scores_and_dto(self):
        svc = AnalysisService(_FakeDb())
        scores = svc.get_strategy_scores(return_dto=False)
        self.assertTrue(isinstance(scores, list) and len(scores) >= 1)
        dtos = svc.get_strategy_scores(return_dto=True)
        self.assertTrue(hasattr(dtos[0], 'stats'))

    def test_symbol_scores_and_time_period_scores(self):
        svc = AnalysisService(_FakeDb())
        ss = svc.get_symbol_scores_by_strategy(strategy_id=1)
        self.assertTrue(isinstance(ss, list))
        ts = svc.get_strategies_scores_by_time_period('2024', 'year')
        self.assertTrue(isinstance(ts, list))

    def test_period_summary_dto(self):
        svc = AnalysisService(_FakeDb())
        dto = svc.get_period_summary('2024', 'year', return_dto=True)
        self.assertTrue(hasattr(dto, 'stats'))


if __name__ == '__main__':
    unittest.main()


