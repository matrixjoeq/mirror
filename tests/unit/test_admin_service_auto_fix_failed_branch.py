#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService
from services.admin_service import DatabaseMaintenanceService


class _TradingServiceStub(TradingService):
    def update_trade_record(self, trade_id, detail_updates):  # type: ignore[override]
        return False, "boom"


class TestAdminServiceAutoFixFailedBranch(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_admin_autofix_fail_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        # 放入一个 trade id 以触发 loop
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted) VALUES (1,'S1','AAA','Alpha','2024-01-01','open',0)", 'params': ()},
        ])
        self.stub = _TradingServiceStub(self.db)
        self.svc = DatabaseMaintenanceService(self.db, self.stub)

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_auto_fix_collects_failed(self):
        out = self.svc.auto_fix([1])
        self.assertEqual(out['fixed'], [])
        self.assertEqual(len(out['failed']), 1)


if __name__ == '__main__':
    unittest.main()


