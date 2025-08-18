#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService
from services.admin_service import DatabaseMaintenanceService


class TestAdminServiceUpdateDetailTriggersRecompute(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_admin_recompute_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.trading = TradingService(self.db)
        self.svc = DatabaseMaintenanceService(self.db, self.trading)
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted) VALUES (1,'S1','AAA','Alpha','2024-01-01','open',0)", 'params': ()},
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (1,'buy',10,10,100,'2024-01-01',1,0)", 'params': ()},
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_update_detail_triggers_recompute(self):
        # 更新 detail 价格，期望成功并触发重算（不对数值断言，仅覆盖路径）
        row = self.db.execute_query("SELECT id FROM trade_details WHERE trade_id=1 LIMIT 1", (), fetch_one=True)
        did = int(row['id'])
        ok, msg = self.svc.update_raw_row('trade_details', did, {'price': 11})
        self.assertTrue(ok, msg)


if __name__ == '__main__':
    unittest.main()


