#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestTradingServicePermanentDeleteFailure(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_permfail_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = TradingService(self.db)

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_permanent_delete_success_path_on_nonexistent(self):
        # Deleting non-existent trade results in no-op success (idempotent)
        ok = self.svc.permanently_delete_trade(999999, 'code', 'CONFIRM', 'r', 'o')
        self.assertTrue(ok)


if __name__ == '__main__':
    unittest.main()


