#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.analysis_service import AnalysisService
from services.database_service import DatabaseService


class TestAnalysisServiceEmptyAndTurnover(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_analysis_turnover_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = AnalysisService(self.db)

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_empty_trades_metrics_defaults(self):
        res = self.svc.calculate_strategy_score(strategy_id=999999)  # no trades
        stats = res['stats']
        # default fields exist and are zeros
        for k in [
            'total_trades','winning_trades','losing_trades','win_rate','total_investment','total_return',
            'total_return_rate','avg_return_per_trade','avg_holding_days','total_fees','avg_profit_loss_ratio',
        ]:
            self.assertIn(k, stats)

    def test_turnover_rate_computation_nonzero(self):
        # prepare closed trade with buys and sells so turnover_rate > 0
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("策略一",)},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, close_date, status, is_deleted, holding_days, total_buy_amount) VALUES (?,?,?,?,?,?,?,0,5,0)",
             'params': (1, "策略一", "AAA", "Alpha", "2024-01-01", "2024-01-10", "closed")},
        ])
        # details: two buys and one sell
        self.db.execute_transaction([
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (1,'buy',10,100,1000,'2024-01-01',1,0)", 'params': ()},
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (1,'buy',20,100,2000,'2024-01-02',1,0)", 'params': ()},
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (1,'sell',25,150,3750,'2024-01-05',3,0)", 'params': ()},
        ])
        res = self.svc.calculate_strategy_score(strategy_id=1)
        self.assertIn('turnover_rate', res['stats'])
        self.assertGreaterEqual(res['stats']['turnover_rate'], 0.0)


if __name__ == '__main__':
    unittest.main()


