#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestTradingServiceGetTradesPaginatedRaw(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_pages_raw_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = TradingService(self.db)
        # Strategy and trades
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
        ])
        for i in range(3):
            ok, _ = self.svc.add_buy_transaction(1, f"A{i}", f"N{i}", 10 + i, 10, "2024-01-01", 0)
            self.assertTrue(ok)

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_return_raw_dicts(self):
        items, total = self.svc.get_trades_paginated(order_by='t.id ASC', page=1, page_size=2, return_dto=False)
        self.assertEqual(len(items), 2)
        self.assertIsInstance(items[0], dict)
        self.assertTrue(total >= 3)


if __name__ == '__main__':
    unittest.main()


