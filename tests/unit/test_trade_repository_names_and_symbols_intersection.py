#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trade_repository import TradeRepository


class TestTradeRepositoryNamesAndSymbolsIntersection(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_repo_intersect_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.repo = TradeRepository(self.db)
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

    def test_intersection_filters(self):
        rows = self.repo.fetch_trades(
            status=None, strategy_id=None, include_deleted=False, order_by='t.id ASC', limit=None,
            symbols=['AAA', 'CCC'], symbol_names=['Alpha', 'Gamma']
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['symbol_code'], 'AAA')


if __name__ == '__main__':
    unittest.main()


