#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trade_repository import TradeRepository


class TestTradeRepositoryDeletedAndStrategyFilter(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_repo_del_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.repo = TradeRepository(self.db)
        # Strategies
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S2",)},
        ])
        # Trades: two active, one deleted
        self.db.execute_transaction([
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted) VALUES (1,'S1','AAA','Alpha','2024-01-01','open',0)", 'params': ()},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted) VALUES (2,'S2','BBB','Beta','2024-01-02','open',0)", 'params': ()},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted) VALUES (1,'S1','CCC','Gamma','2024-01-03','open',1)", 'params': ()},
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_include_deleted_true_vs_false(self):
        rows_excl = self.repo.fetch_trades(None, None, False, 't.id ASC', None)
        self.assertEqual(len(rows_excl), 2)
        rows_incl = self.repo.fetch_trades(None, None, True, 't.id ASC', None)
        self.assertEqual(len(rows_incl), 3)

    def test_strategy_filter(self):
        rows_s2 = self.repo.fetch_trades(None, 2, False, 't.id ASC', None)
        self.assertEqual(len(rows_s2), 1)
        self.assertEqual(rows_s2[0]['symbol_code'], 'BBB')


if __name__ == '__main__':
    unittest.main()


