#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService
from services.admin_service import DatabaseMaintenanceService


class TestAdminServiceNoUpdatesBranch(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_admin_noupd_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.trading = TradingService(self.db)
        self.svc = DatabaseMaintenanceService(self.db, self.trading)
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted) VALUES (1,'S1','AAA','Alpha','2024-01-01','open',0)", 'params': ()},
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_update_raw_row_no_allowed_fields(self):
        ok, msg = self.svc.update_raw_row('trades', 1, {'not_allowed_field': 'x'})
        self.assertFalse(ok)
        self.assertIn('没有可更新字段', msg)


if __name__ == '__main__':
    unittest.main()


