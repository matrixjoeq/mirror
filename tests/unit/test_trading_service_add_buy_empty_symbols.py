#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestTradingServiceAddBuyEmptySymbols(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_empty_symbols_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = TradingService(self.db)
        # Strategy
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_add_buy_symbols_empty(self):
        ok, msg = self.svc.add_buy_transaction(1, "", "", 10, 10, "2024-01-01", 0)
        self.assertFalse(ok)
        self.assertIn("不能为空", msg)


if __name__ == '__main__':
    unittest.main()


