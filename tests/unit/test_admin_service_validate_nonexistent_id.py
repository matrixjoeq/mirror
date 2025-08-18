#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService
from services.admin_service import DatabaseMaintenanceService


class TestAdminServiceValidateNonexistentId(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_admin_val_nf_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = DatabaseMaintenanceService(self.db, TradingService(self.db))

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_validate_database_nonexistent_id(self):
        res = self.svc.validate_database(999999)
        self.assertEqual(res['summary']['trade_issue_count'], 0)
        self.assertEqual(res['summary']['detail_issue_count'], 0)


if __name__ == '__main__':
    unittest.main()


