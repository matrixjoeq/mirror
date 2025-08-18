#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestTradingServiceOversellAndAnomalies(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_oversell_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = TradingService(self.db)
        # strategy and trade
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
        ])
        ok, res = self.svc.add_buy_transaction(1, "AAA", "Alpha", 10, 100, "2024-01-01", 0)
        self.assertTrue(ok)
        self.trade_id = int(res)

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_oversell_does_not_crash_remaining_map(self):
        # 先插入一笔卖出超过总买入数量，compute_buy_detail_remaining_map 应可返回非负剩余
        self.db.execute_transaction([
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (?,?, ?, ?, ?, ?, ?, 0)",
             'params': (self.trade_id, 'sell', 12, 150, 150*12, '2024-01-02', 0)},
        ])
        remap = self.svc.compute_buy_detail_remaining_map(self.trade_id)
        # 总剩余不会为负
        total_remaining = sum(remap.values())
        self.assertGreaterEqual(total_remaining, 0)


if __name__ == '__main__':
    unittest.main()


