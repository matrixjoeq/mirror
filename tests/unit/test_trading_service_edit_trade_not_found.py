#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestTradingServiceEditTradeNotFound(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_edit_nf_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = TradingService(self.db)

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_edit_trade_not_found(self):
        ok, msg = self.svc.edit_trade(999999, {'symbol_name': 'X'}, 'reason')
        self.assertFalse(ok)
        self.assertIn('不存在', msg)


if __name__ == '__main__':
    unittest.main()


