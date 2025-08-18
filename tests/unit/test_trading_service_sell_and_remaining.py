#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestTradingServiceSellAndRemaining(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_sell_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = TradingService(self.db)
        # strategy
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_compute_remaining_and_sell_success(self):
        # two buys
        ok1, t1 = self.svc.add_buy_transaction(1, "AAA", "Alpha", 10, 100, "2024-01-01", 1)
        self.assertTrue(ok1)
        trade_id = int(t1)
        ok2, _ = self.svc.add_buy_transaction(1, "AAA", "Alpha", 20, 100, "2024-01-02", 1)
        self.assertTrue(ok2)

        # remaining before sell
        remap_before = self.svc.compute_buy_detail_remaining_map(trade_id)
        self.assertEqual(sum(remap_before.values()), 200)

        # sell 150
        ok3, msg3 = self.svc.add_sell_transaction(trade_id, 25, 150, "2024-01-03", 3, "take profit")
        self.assertTrue(ok3, msg3)

        # remaining after sell (should be 50 left)
        remap_after = self.svc.compute_buy_detail_remaining_map(trade_id)
        self.assertEqual(sum(remap_after.values()), 50)

        # get trade by id (non-deleted) still exists
        t = self.svc.get_trade_by_id(trade_id)
        self.assertIsNotNone(t)


if __name__ == '__main__':
    unittest.main()


