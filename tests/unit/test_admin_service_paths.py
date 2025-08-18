#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService
from services.admin_service import DatabaseMaintenanceService


class TestAdminServicePaths(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_adminsvc_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.trading = TradingService(self.db)
        self.svc = DatabaseMaintenanceService(self.db, self.trading)
        # 基础策略
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_update_raw_row_invalid_table_and_missing(self):
        ok, msg = self.svc.update_raw_row('invalid', 1, {'symbol_code': 'X'})
        self.assertFalse(ok)
        self.assertIn('不支持', msg)

        ok2, msg2 = self.svc.update_raw_row('trades', 9999, {'symbol_code': 'X'})
        self.assertFalse(ok2)
        self.assertIn('不存在', msg2)

        ok3, msg3 = self.svc.update_raw_row('trade_details', 9999, {'price': 1})
        self.assertFalse(ok3)
        self.assertIn('不存在', msg3)

    def test_validate_database_empty(self):
        res = self.svc.validate_database()
        self.assertIn('summary', res)
        self.assertIn('trade_issue_count', res['summary'])


if __name__ == '__main__':
    unittest.main()


