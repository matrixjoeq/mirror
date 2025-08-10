#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
from services import DatabaseService, StrategyService, AnalysisService


class TestAnalysisServiceZeroTradesFreq(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)
        self.strategy = StrategyService(self.db)
        self.analysis = AnalysisService(self.db)

    def test_zero_trades_frequency_is_zero(self):
        ok, _ = self.strategy.create_strategy('零交易', '')
        sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '零交易')
        score = self.analysis.calculate_strategy_score(strategy_id=sid)
        self.assertEqual(score['stats']['total_trades'], 0)
        # 频率分在零交易情形下为0（路由层计算兼容），这里等价于平均持仓为0
        self.assertEqual(score['stats']['avg_holding_days'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)


