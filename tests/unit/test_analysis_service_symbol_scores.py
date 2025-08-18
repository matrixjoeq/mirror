#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.analysis_service import AnalysisService
from services.strategy_service import StrategyService


class TestAnalysisServiceSymbolScores(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_analysis_symbol_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.analysis = AnalysisService(self.db)
        self.strategy = StrategyService(self.db)
        ok, msg = self.strategy.create_strategy('S1', 'd')
        assert ok, msg
        # Two symbols: one winning, one losing
        self.db.execute_transaction([
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, close_date, status, is_deleted, holding_days, total_buy_amount) VALUES (1,'S1','AAA','Alpha','2024-01-01','2024-01-10','closed',0,9,0)", 'params': ()},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, close_date, status, is_deleted, holding_days, total_buy_amount) VALUES (1,'S1','BBB','Beta','2024-02-01','2024-02-10','closed',0,9,0)", 'params': ()},
        ])
        # AAA: profit
        self.db.execute_transaction([
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (1,'buy',10,100,1000,'2024-01-01',1,0)", 'params': ()},
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (1,'sell',12,100,1199,'2024-01-10',1,0)", 'params': ()},
        ])
        # BBB: loss
        self.db.execute_transaction([
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (2,'buy',10,100,1000,'2024-02-01',1,0)", 'params': ()},
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (2,'sell',9,100,899,'2024-02-10',1,0)", 'params': ()},
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_get_symbol_scores_by_strategy(self):
        scores = self.analysis.get_symbol_scores_by_strategy(strategy_id=1, return_dto=True)
        self.assertTrue(scores)
        self.assertTrue(hasattr(scores[0], 'stats'))


if __name__ == '__main__':
    unittest.main()


