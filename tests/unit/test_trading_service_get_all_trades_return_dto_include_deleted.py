#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestTradingServiceGetAllTradesReturnDtoIncludeDeleted(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_all_dto_deleted_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = TradingService(self.db)
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted) VALUES (1,'S1','AAA','Alpha','2024-01-01','open',1)", 'params': ()},
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_get_all_trades_return_dto_include_deleted(self):
        rows = self.svc.get_all_trades(status=None, strategy=None, include_deleted=True, return_dto=True)
        self.assertTrue(rows)
        self.assertTrue(hasattr(rows[0], 'strategy_name'))


if __name__ == '__main__':
    unittest.main()


