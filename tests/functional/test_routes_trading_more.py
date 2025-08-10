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


class TestRoutesTradingMore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()

        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['DATABASE_PATH'] = self.tmp.name

        self.db = DatabaseService(self.tmp.name)
        self.trading = TradingService(self.db)
        self.strategy = StrategyService(self.db)

        self.app.db_service = self.db
        self.app.trading_service = self.trading
        self.app.strategy_service = self.strategy

        self.client = self.app.test_client()

        ok, _ = self.strategy.create_strategy('功能交易策略', '')
        self.sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '功能交易策略')

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_add_sell_get_nonexistent_redirect(self):
        resp = self.client.get('/add_sell/999999')
        self.assertIn(resp.status_code, (302, 303))

    def test_edit_trade_get_nonexistent_redirect(self):
        resp = self.client.get('/edit_trade/999999')
        self.assertIn(resp.status_code, (302, 303))

    def test_trade_details_page(self):
        ok, trade_id = self.trading.add_buy_transaction(self.sid, 'DET', '详', Decimal('10'), 1, '2025-01-01')
        self.assertTrue(ok)
        resp = self.client.get(f'/trade_details/{trade_id}')
        self.assertEqual(resp.status_code, 200)

    def test_deleted_trades_content(self):
        ok, trade_id = self.trading.add_buy_transaction(self.sid, 'DEL2', '删二', Decimal('10'), 1, '2025-01-01')
        self.assertTrue(ok)
        self.assertTrue(self.trading.soft_delete_trade(trade_id, 'X', '功能删除'))
        resp = self.client.get('/deleted_trades')
        self.assertEqual(resp.status_code, 200)


if __name__ == '__main__':
    unittest.main(verbosity=2)


