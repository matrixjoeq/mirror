#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trade_repository import TradeRepository


class TestTradeRepositoryOrderAndCount(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_repo_order_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.repo = TradeRepository(self.db)
        # minimal data
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted) VALUES (1,'S1','AAA','Alpha','2024-01-01','open',0)", 'params': ()},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted) VALUES (1,'S1','BBB','Beta','2024-01-02','open',0)", 'params': ()},
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_order_and_limit_offset(self):
        rows = self.repo.fetch_trades(None, None, False, 't.open_date ASC', 1, 0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['symbol_code'], 'AAA')
        rows2 = self.repo.fetch_trades(None, None, False, 't.open_date ASC', 1, 1)
        self.assertEqual(rows2[0]['symbol_code'], 'BBB')

    def test_count_trades(self):
        cnt = self.repo.count_trades(None, None, False)
        self.assertEqual(cnt, 2)


if __name__ == '__main__':
    unittest.main()


