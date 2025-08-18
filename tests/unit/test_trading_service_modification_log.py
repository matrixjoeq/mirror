#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestTradingServiceModificationLog(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_mod_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = TradingService(self.db)
        # Prepare a trade to satisfy FK
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S",)},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted) VALUES (1,'S','AAA','Alpha','2024-01-01','open',0)", 'params': ()},
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_record_and_fetch_modifications(self):
        # 写入一条修改历史并读取
        ok = self.svc.record_modification(1, None, 'edit_trade', 'symbol_name', 'Old', 'New', 'reason')
        self.assertTrue(ok)
        mods = self.svc.get_trade_modifications(1)
        self.assertTrue(len(mods) >= 1)
        self.assertEqual(mods[0]['trade_id'], 1)


if __name__ == '__main__':
    unittest.main()


