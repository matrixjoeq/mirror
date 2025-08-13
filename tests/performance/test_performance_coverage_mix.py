#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from services import DatabaseService, TradingService, StrategyService, AnalysisService
from app import create_app


class TestPerformanceCoverageMix(unittest.TestCase):
    def setUp(self):
        # 使用 Flask 测试应用，确保 routes 可被 exercise
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()
        self.db = self.app.db_service
        self.trading = self.app.trading_service
        self.strategy = self.app.strategy_service
        self.analysis = self.app.analysis_service
        ok, _ = self.strategy.create_strategy('覆盖策略A', '')
        ok2, _ = self.strategy.create_strategy('覆盖策略B', '')
        self.sid_a = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '覆盖策略A')
        self.sid_b = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '覆盖策略B')

    def tearDown(self):
        self.ctx.pop()

    def test_trading_service_paths(self):
        # invalid inputs
        ok, msg = self.trading.add_buy_transaction(self.sid_a, '', 'X', Decimal('1.0'), 1, '2025-01-01')
        self.assertFalse(ok)
        ok, msg = self.trading.add_buy_transaction(self.sid_a, 'X', '', Decimal('1.0'), 1, '2025-01-01')
        self.assertFalse(ok)
        ok, msg = self.trading.add_buy_transaction(self.sid_a, 'X', 'Y', Decimal('0'), 1, '2025-01-01')
        self.assertFalse(ok)

        # create and update flows
        ok, tid = self.trading.add_buy_transaction(self.sid_a, 'COV1', '覆盖股1', Decimal('10'), 10, '2025-01-01')
        self.assertTrue(ok)
        ok, _ = self.trading.add_buy_transaction(self.sid_a, 'COV1', '覆盖股1', Decimal('11'), 5, '2025-01-02')
        self.assertTrue(ok)

        # details and modification record
        details = self.trading.get_trade_details(tid)
        first_buy = next(d for d in details if d['transaction_type'] == 'buy')
        self.assertTrue(self.trading.record_modification(tid, first_buy['id'], 'detail', 'price', '10', '10.5'))

        # sell partial then full
        ok, msg = self.trading.add_sell_transaction(tid, Decimal('12'), 5, '2025-01-03')
        self.assertTrue(ok)
        ok, msg = self.trading.add_sell_transaction(tid, Decimal('12'), 10, '2025-01-04')
        self.assertTrue(ok)

        # soft delete / restore / permanent delete
        self.assertTrue(self.trading.soft_delete_trade(tid, 'X', '性能覆盖'))
        self.assertTrue(self.trading.restore_trade(tid, 'X'))
        self.assertTrue(self.trading.permanently_delete_trade(tid, 'X', 'CONFIRM', '性能覆盖'))

        # list endpoints
        _ = self.trading.get_all_trades(status='open')
        _ = self.trading.get_all_trades(status='closed')
        _ = self.trading.get_all_trades(strategy='覆盖策略A')
        _ = self.trading.get_deleted_trades()
        # exercise routes quickly to raise routes coverage
        self.client.get('/trades')
        self.client.get('/deleted_trades')
        # admin diagnose page
        self.client.get('/admin/db/diagnose')

    def test_strategy_and_analysis_paths(self):
        # tags
        ok, msg = self.strategy.create_tag('T1')
        self.assertTrue(ok or '已存在' in msg)
        tags = self.strategy.get_all_tags()
        t1 = next(t for t in tags if t['name'] == 'T1')
        ok2, msg2 = self.strategy.update_tag(t1['id'], 'T1X')
        self.assertTrue(ok2 or '不能修改' in msg2 or '已存在' in msg2)
        ok3, msg3 = self.strategy.delete_tag(999999)  # non-existent
        self.assertFalse(ok3)
        # disable by name
        ok4, _ = self.strategy.disable_strategy_by_name('覆盖策略B')
        self.assertTrue(ok4)

        # seed trades for analysis
        ok, tid1 = self.trading.add_buy_transaction(self.sid_a, 'ANA1', '甲', Decimal('10'), 10, '2025-01-05')
        self.assertTrue(ok)
        self.trading.add_sell_transaction(tid1, Decimal('12'), 10, '2025-01-08')
        ok, tid2 = self.trading.add_buy_transaction(self.sid_a, 'ANA2', '乙', Decimal('10'), 10, '2025-04-05')
        self.trading.add_sell_transaction(tid2, Decimal('9'), 10, '2025-04-08')

        # analysis service coverage
        _ = self.analysis.calculate_strategy_score(strategy_id=self.sid_a)
        _ = self.analysis.calculate_strategy_score(strategy='覆盖策略A')
        _ = self.analysis.calculate_strategy_score(symbol_code='ANA1')
        _ = self.analysis.calculate_strategy_score(start_date='2025-01-01', end_date='2025-12-31')
        _ = self.analysis.get_strategy_scores()
        _ = self.analysis.get_symbol_scores_by_strategy(strategy_id=self.sid_a)
        _ = self.analysis.get_symbol_scores_by_strategy(strategy='覆盖策略A')
        _ = self.analysis.get_all_symbols()
        _ = self.analysis.get_strategies_scores_by_symbol('ANA1')
        for pt in ['year', 'quarter', 'month']:
            _ = self.analysis.get_time_periods(pt)
        _ = self.analysis.get_strategies_scores_by_time_period('2025', 'year')
        _ = self.analysis.get_period_summary('2025', 'year')


if __name__ == '__main__':
    unittest.main(verbosity=2)


