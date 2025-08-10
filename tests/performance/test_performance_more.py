#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
import os
import sys
import time
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from services import DatabaseService, TradingService, StrategyService, AnalysisService


class TestPerformanceMore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)
        self.trading = TradingService(self.db)
        self.strategy = StrategyService(self.db)
        self.analysis = AnalysisService(self.db)
        ok, _ = self.strategy.create_strategy('性能更多', '')
        self.sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '性能更多')

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_bulk_update_and_score_performance(self):
        # 创建 200 笔买入并部分卖出
        for i in range(200):
            ok, trade_id = self.trading.add_buy_transaction(self.sid, f'M{i:03d}', f'名{i}', Decimal('10'), 10, '2025-01-01')
            self.assertTrue(ok)
            if i % 7 == 0:
                ok, _ = self.trading.add_sell_transaction(trade_id, Decimal('11'), 10, '2025-01-10')
                self.assertTrue(ok)

        # 组合过滤查询性能
        t0 = time.perf_counter()
        _ = self.trading.get_all_trades(status='open')
        _ = self.trading.get_all_trades(status='closed')
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 1.5)

        # 评分计算性能
        t1 = time.perf_counter()
        _ = self.analysis.calculate_strategy_score(strategy_id=self.sid)
        e1 = time.perf_counter() - t1
        self.assertLess(e1, 2.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)


