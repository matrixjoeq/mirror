#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService
from services.admin_service import DatabaseMaintenanceService


class _TradingServiceFlip(TradingService):
    def __init__(self, db):
        super().__init__(db)
        self._flip = False

    def update_trade_record(self, trade_id, detail_updates):  # type: ignore[override]
        self._flip = not self._flip
        return (True, "ok") if self._flip else (False, "boom")


class TestAdminServiceAutofixScanAndMix(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_admin_autofix_mix_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.trading = _TradingServiceFlip(self.db)
        self.svc = DatabaseMaintenanceService(self.db, self.trading)
        # three trades to scan
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted) VALUES (1,'S1','A','a','2024-01-01','open',0)", 'params': ()},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted) VALUES (1,'S1','B','b','2024-01-02','open',0)", 'params': ()},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted) VALUES (1,'S1','C','c','2024-01-03','open',0)", 'params': ()},
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_autofix_scan_none_and_mixed_results(self):
        out = self.svc.auto_fix(None)
        self.assertTrue(len(out['fixed']) >= 1)
        self.assertTrue(len(out['failed']) >= 1)


if __name__ == '__main__':
    unittest.main()


