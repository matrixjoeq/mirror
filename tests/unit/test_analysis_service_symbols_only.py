#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
from decimal import Decimal

from services import DatabaseService, TradingService, StrategyService, AnalysisService


class TestAnalysisServiceSymbolsOnly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)
        self.strategy = StrategyService(self.db)
        self.trading = TradingService(self.db)
        self.analysis = AnalysisService(self.db)
        ok, _ = self.strategy.create_strategy('符号测试', '')
        self.sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '符号测试')

    def test_get_symbol_scores_by_strategy(self):
        # 创建两个标的，其中一个闭合，一个未闭合
        ok, t1 = self.trading.add_buy_transaction(self.sid, 'SS1', '标的一', Decimal('10.00'), 100, '2025-01-01')
        self.trading.add_sell_transaction(t1, Decimal('11.00'), 100, '2025-01-05')
        ok, _ = self.trading.add_buy_transaction(self.sid, 'SS2', '标的二', Decimal('10.00'), 100, '2025-01-10')

        scores = self.analysis.get_symbol_scores_by_strategy(strategy_id=self.sid)
        # 至少包含已闭合标的；未闭合标的在实现上可能被列出但其 total_trades=0，我们过滤统计
        self.assertTrue(any(s.get('symbol_code') == 'SS1' for s in scores))
        self.assertTrue(all((s['stats']['total_trades'] > 0) == (s.get('symbol_code') == 'SS1') for s in scores))


if __name__ == '__main__':
    unittest.main(verbosity=2)


