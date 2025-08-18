#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.analysis_service import AnalysisService
from services.strategy_service import StrategyService


class TestAnalysisServiceApiLike(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_analysis_api_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.analysis = AnalysisService(self.db)
        self.strategy = StrategyService(self.db)
        ok, msg = self.strategy.create_strategy('S1', 'd')
        assert ok, msg
        # Insert closed trade with details for symbol filter
        self.db.execute_transaction([
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, close_date, status, is_deleted, holding_days, total_buy_amount) VALUES (1,'S1','AAA','Alpha','2024-01-01','2024-01-10','closed',0,9,0)", 'params': ()},
        ])
        self.db.execute_transaction([
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (1,'buy',10,100,1001,'2024-01-01',1,0)", 'params': ()},
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (1,'sell',15,100,1499,'2024-01-10',1,0)", 'params': ()},
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_get_strategy_scores_and_period_summary(self):
        scores = self.analysis.get_strategy_scores(return_dto=True)
        self.assertTrue(scores)
        self.assertTrue(hasattr(scores[0], 'stats'))
        ps = self.analysis.get_period_summary('2024', 'year', return_dto=True)
        self.assertTrue(hasattr(ps, 'stats'))

    def test_symbol_code_filter_and_attach_scores(self):
        res = self.analysis.calculate_strategy_score(strategy_id=1, symbol_code='AAA', start_date='2024-01-01', end_date='2024-12-31')
        out = self.analysis.attach_score_fields(res)
        self.assertIn('total_score', out)


if __name__ == '__main__':
    unittest.main()


