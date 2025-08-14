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


class TestApiTrendSuccess(unittest.TestCase):
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

        ok, _ = self.strategy.create_strategy('趋势X', '')
        self.sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '趋势X')
        # 数据跨2个月
        ok, t1 = self.trading.add_buy_transaction(self.sid, 'TS1', '甲', Decimal('10'), 1, '2025-01-02')
        self.trading.add_sell_transaction(t1, Decimal('11'), 1, '2025-01-03')
        ok, t2 = self.trading.add_buy_transaction(self.sid, 'TS2', '乙', Decimal('10'), 1, '2025-02-02')
        self.trading.add_sell_transaction(t2, Decimal('9'), 1, '2025-02-03')

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_trend_success(self):
        r = self.client.get(f'/api/strategy_trend?strategy_id={self.sid}&period_type=month')
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertTrue(j.get('success'))
        self.assertIsInstance(j.get('data'), list)
        self.assertGreaterEqual(len(j.get('data')), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)


