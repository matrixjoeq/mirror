#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
import os
from services import DatabaseService, TradingService, StrategyService


class TestTradingServiceValidations(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)
        self.trading = TradingService(self.db)
        self.strategy = StrategyService(self.db)
        self.strategy.create_strategy('VAL', '校验')
        self.sid = self.strategy.get_all_strategies()[0]['id']

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_invalid_date_buy(self):
        ok, msg = self.trading.add_buy_transaction(
            strategy=self.sid,
            symbol_code='V1',
            symbol_name='校验1',
            price=1.0,
            quantity=1,
            transaction_date='2025/01/01'
        )
        self.assertFalse(ok)
        self.assertIn('日期', msg)

    def test_invalid_date_sell(self):
        ok, tid = self.trading.add_buy_transaction(
            strategy=self.sid,
            symbol_code='V2',
            symbol_name='校验2',
            price=1.0,
            quantity=1,
            transaction_date='2025-01-01'
        )
        self.assertTrue(ok)
        ok2, msg2 = self.trading.add_sell_transaction(
            trade_id=tid,
            price=1.1,
            quantity=1,
            transaction_date='2025/01/01'
        )
        self.assertFalse(ok2)
        self.assertIn('日期', msg2)


if __name__ == '__main__':
    unittest.main(verbosity=2)


