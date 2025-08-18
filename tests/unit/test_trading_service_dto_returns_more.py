#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestTradingServiceDtoReturnsMore(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_dto2_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = TradingService(self.db)
        # Strategy and a trade with a detail
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
        ])
        ok, res = self.svc.add_buy_transaction(1, "AAA", "Alpha", 10, 100, "2024-01-01", 1)
        self.assertTrue(ok)
        self.trade_id = int(res)

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_get_trade_details_return_dto(self):
        items = self.svc.get_trade_details(self.trade_id, return_dto=True)
        self.assertTrue(items)
        self.assertTrue(hasattr(items[0], 'amount'))

    def test_get_deleted_trades_return_dto(self):
        # Soft delete the trade
        self.assertTrue(self.svc.soft_delete_trade(self.trade_id, 'code', 'reason'))
        deleted = self.svc.get_deleted_trades(return_dto=True)
        self.assertTrue(deleted)
        self.assertTrue(hasattr(deleted[0], 'strategy_name'))

    def test_get_trade_by_id_include_deleted(self):
        t = self.svc.get_trade_by_id(self.trade_id, include_deleted=True)
        self.assertIsNotNone(t)


if __name__ == '__main__':
    unittest.main()


