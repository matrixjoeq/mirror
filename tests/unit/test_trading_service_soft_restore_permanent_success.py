#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestTradingServiceSoftRestorePermanentSuccess(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_soft_restore_perm_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = TradingService(self.db)
        # strategy
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
        ])
        ok, res = self.svc.add_buy_transaction(1, "AAA", "Alpha", 10, 100, "2024-01-01", 1)
        self.assertTrue(ok)
        self.trade_id = int(res)
        # add sell and record a modification row to exercise deletion order
        ok2, _ = self.svc.add_sell_transaction(self.trade_id, 12, 50, "2024-01-10", 1, "take profit")
        self.assertTrue(ok2)
        self.assertTrue(self.svc.record_modification(self.trade_id, None, 'edit_trade', 'symbol_name', 'A', 'B', 'reason'))

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_soft_restore_and_permanent_delete_success(self):
        self.assertTrue(self.svc.soft_delete_trade(self.trade_id, 'code', 'del', 'note'))
        self.assertTrue(self.svc.restore_trade(self.trade_id, 'code', 'note'))
        self.assertTrue(self.svc.permanently_delete_trade(self.trade_id, 'code', 'CONFIRM', 'r', 'o'))


if __name__ == '__main__':
    unittest.main()


