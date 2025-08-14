#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app
from services import DatabaseService, TradingService, StrategyService, AnalysisService


class TestRoutesAnalysisMore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.app.config['DATABASE_PATH'] = self.tmp.name
        self.db = DatabaseService(self.tmp.name)
        self.trading = TradingService(self.db)
        self.strategy = StrategyService(self.db)
        self.analysis = AnalysisService(self.db)
        self.app.db_service = self.db
        self.app.trading_service = self.trading
        self.app.strategy_service = self.strategy
        self.app.analysis_service = self.analysis
        self.client = self.app.test_client()

        # seed data
        ok, _ = self.strategy.create_strategy('分析策略X', '')
        self.sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '分析策略X')
        ok, t1 = self.trading.add_buy_transaction(self.sid, 'AN1', '甲', Decimal('10'), 1, '2025-01-02')
        self.trading.add_sell_transaction(t1, Decimal('11'), 1, '2025-01-03')
        ok, t2 = self.trading.add_buy_transaction(self.sid, 'AN2', '乙', Decimal('10'), 1, '2025-02-02')
        self.trading.add_sell_transaction(t2, Decimal('9'), 1, '2025-02-05')

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_strategy_detail_multiple_sorts_and_invalid(self):
        # valid sorts
        for sort_by in ['total_score', 'win_rate_score', 'profit_loss_ratio_score', 'frequency_score', 'symbol_code']:
            r = self.client.get(f'/strategy_detail/{self.sid}?sort_by={sort_by}&sort_order=desc')
            self.assertEqual(r.status_code, 200)
        # invalid sort param falls through
        r2 = self.client.get(f'/strategy_detail/{self.sid}?sort_by=unknown&sort_order=asc')
        self.assertEqual(r2.status_code, 200)

    def test_strategy_detail_invalid_id_redirect(self):
        r = self.client.get('/strategy_detail/999999')
        self.assertIn(r.status_code, (302, 303))

    def test_api_strategy_score_with_symbol(self):
        r = self.client.get(f'/api/strategy_score?strategy_id={self.sid}&symbol_code=AN1')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json().get('success'))


if __name__ == '__main__':
    unittest.main(verbosity=2)


