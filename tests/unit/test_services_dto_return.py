#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from typing import Any, Optional, Tuple

from services.analysis_service import AnalysisService
from services.trading_service import TradingService


class _FakeDb:
    """Minimal fake db for services that only need execute_query."""

    def execute_query(self, query: str, params: Optional[Tuple[Any, ...]] = None, fetch_one: bool = False, fetch_all: bool = True):
        return []


class TestServicesDtoReturn(unittest.TestCase):
    def test_analysis_service_calculate_strategy_score_returns_dto_when_flag_true(self):
        svc = AnalysisService(_FakeDb())
        result = svc.calculate_strategy_score(return_dto=True)
        self.assertTrue(hasattr(result, 'stats'))
        self.assertIsInstance(result.stats, dict)
        self.assertEqual(result.stats.get('total_trades', None), 0)

    def test_trading_service_get_trade_details_returns_dto_list_when_flag_true(self):
        svc = TradingService(_FakeDb())
        dto_list = svc.get_trade_details(trade_id=1, return_dto=True)
        self.assertIsInstance(dto_list, list)
        self.assertEqual(dto_list, [])


if __name__ == '__main__':
    unittest.main()


