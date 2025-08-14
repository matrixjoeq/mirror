#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app
from services import DatabaseService, TradingService, StrategyService


class TestAnalysisPagesWithData(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.app.config['DATABASE_PATH'] = self.tmp.name
        self.db = DatabaseService(self.tmp.name)
        self.trading = TradingService(self.db)
        self.strategy = StrategyService(self.db)
        self.app.db_service = self.db
        self.client = self.app.test_client()

        # data
        ok, _ = self.strategy.create_strategy('功能评分策略', '')
        self.sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '功能评分策略')
        ok, t1 = self.trading.add_buy_transaction(self.sid, 'CMP1', '甲', Decimal('10'), 2, '2025-01-10')
        self.trading.add_sell_transaction(t1, Decimal('11'), 2, '2025-01-15')

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_strategy_scores_and_symbol_comparison(self):
        # pages render with data present
        self.assertEqual(self.client.get('/strategy_scores').status_code, 200)
        self.assertEqual(self.client.get('/symbol_comparison').status_code, 200)

    def test_api_strategy_score_with_name_and_window(self):
        # use strategy name and date window filters
        r = self.client.get('/api/strategy_score', query_string={
            'strategy': '功能评分策略',
            'start_date': '2025-01-01',
            'end_date': '2025-12-31'
        })
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertTrue(j.get('success'))
        self.assertIn('stats', j.get('data', {}))


if __name__ == '__main__':
    unittest.main(verbosity=2)


