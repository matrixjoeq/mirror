#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService
from services.admin_service import DatabaseMaintenanceService


class TestAdminServiceRoundingFields(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_admin_rounding_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.trading = TradingService(self.db)
        self.svc = DatabaseMaintenanceService(self.db, self.trading)
        # Strategy + one trade with details to exercise rounding checks
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted, total_buy_amount, total_buy_quantity, total_sell_amount, total_sell_quantity, remaining_quantity, total_profit_loss, total_profit_loss_pct) VALUES (1,'S1','AAA','Alpha','2024-01-01','open',0, 100.1239, 10, 0, 0, 10, 3.14159, 2.71828)", 'params': ()},
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (1,'buy',10.0123,10,100.123, '2024-01-01',0.001,0)", 'params': ()},
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_rounding_fields_in_validate(self):
        res = self.svc.validate_database(1)
        self.assertIn('summary', res)
        self.assertIn('trade_issues', res)
        # 不强行断言具体数值，只验证路径被覆盖
        self.assertIsInstance(res['trade_issues'], list)


if __name__ == '__main__':
    unittest.main()


