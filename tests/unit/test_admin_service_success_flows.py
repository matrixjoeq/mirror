#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService
from services.admin_service import DatabaseMaintenanceService


class TestAdminServiceSuccessFlows(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_admin_success_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.trading = TradingService(self.db)
        self.svc = DatabaseMaintenanceService(self.db, self.trading)
        # Data: strategy, trade and details (2 buys, 1 sell)
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted, holding_days, total_buy_amount) VALUES (1,'S1','AAA','Alpha','2024-01-01','open',0,0,0)", 'params': ()},
        ])
        self.db.execute_transaction([
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (1,'buy',10,100,1001,'2024-01-01',1,0)", 'params': ()},
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (1,'buy',20,100,2002,'2024-01-02',2,0)", 'params': ()},
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (1,'sell',25,150,3747,'2024-01-05',3,0)", 'params': ()},
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_validate_auto_fix_and_update_raw_row(self):
        # Validate should run and produce a summary
        result = self.svc.validate_database(1)
        self.assertIn('summary', result)
        # Auto-fix should attempt update and return fixed or failed arrays
        out = self.svc.auto_fix([1])
        self.assertIn('fixed', out)
        self.assertIn('failed', out)

        # Update trades row
        ok, msg = self.svc.update_raw_row('trades', 1, {'symbol_name': 'AlphaX'})
        self.assertTrue(ok, msg)

        # Update detail row (grab an id)
        row = self.db.execute_query("SELECT id FROM trade_details WHERE trade_id = 1 LIMIT 1", (), fetch_one=True)
        self.assertIsNotNone(row)
        detail_id = int(row['id'])
        ok2, msg2 = self.svc.update_raw_row('trade_details', detail_id, {'price': 11})
        self.assertTrue(ok2, msg2)


if __name__ == '__main__':
    unittest.main()


