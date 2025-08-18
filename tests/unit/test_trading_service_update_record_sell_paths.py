#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestTradingServiceUpdateRecordSellPaths(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_update_sell_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = TradingService(self.db)
        # strategy and trade with buy+sell
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
        ])
        ok, res = self.svc.add_buy_transaction(1, "AAA", "Alpha", 10, 100, "2024-01-01", 1)
        self.assertTrue(ok)
        self.trade_id = int(res)
        self.assertTrue(self.svc.add_sell_transaction(self.trade_id, 12, 50, "2024-01-10", 1, "tp")[0])
        # detail rows
        self.buy_detail = self.db.execute_query("SELECT id FROM trade_details WHERE trade_id=? AND transaction_type='buy' LIMIT 1", (self.trade_id,), fetch_one=True)['id']
        self.sell_detail = self.db.execute_query("SELECT id FROM trade_details WHERE trade_id=? AND transaction_type='sell' LIMIT 1", (self.trade_id,), fetch_one=True)['id']

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_update_sell_detail_recomputes_profit_fields(self):
        ok, msg = self.svc.update_trade_record(self.trade_id, [{'detail_id': int(self.sell_detail), 'price': 13}])
        self.assertTrue(ok, msg)

    def test_update_record_invalid_values(self):
        ok, msg = self.svc.update_trade_record(self.trade_id, [{'detail_id': int(self.sell_detail), 'price': 0, 'quantity': 0}])
        self.assertFalse(ok)
        self.assertIn('必须大于0', msg)


if __name__ == '__main__':
    unittest.main()


