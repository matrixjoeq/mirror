#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
from decimal import Decimal

from services import DatabaseService, TradingService, StrategyService, AnalysisService


class TestAnalysisServiceFillGaps(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)
        self.strategy = StrategyService(self.db)
        self.trading = TradingService(self.db)
        self.analysis = AnalysisService(self.db)
        ok, _ = self.strategy.create_strategy('空数据策略', '')
        self.sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '空数据策略')

    def test_calculate_strategy_score_no_trades(self):
        score = self.analysis.calculate_strategy_score(strategy_id=self.sid)
        stats = score['stats']
        self.assertEqual(stats['total_trades'], 0)
        self.assertEqual(stats['win_rate'], 0)
        self.assertEqual(stats['avg_profit_loss_ratio'], 0.0)

    def test_get_time_periods_all_types(self):
        # 创建不同月份的交易，覆盖 year/quarter/month 列表生成路径
        ok, t1 = self.trading.add_buy_transaction(self.sid, 'A', '一', Decimal('10'), 1, '2025-01-02')
        self.trading.add_sell_transaction(t1, Decimal('11'), 1, '2025-01-03')
        ok, t2 = self.trading.add_buy_transaction(self.sid, 'B', '二', Decimal('10'), 1, '2025-04-02')
        self.trading.add_sell_transaction(t2, Decimal('9'), 1, '2025-04-05')

        years = self.analysis.get_time_periods('year')
        quarters = self.analysis.get_time_periods('quarter')
        months = self.analysis.get_time_periods('month')
        self.assertIn('2025', years)
        self.assertTrue(any(q.startswith('2025-Q') for q in quarters))
        self.assertTrue(any(m.startswith('2025-') for m in months))

    def test_get_strategies_scores_by_symbol_and_time_period_filters(self):
        # 数据：两只股票分别有交易
        ok, t1 = self.trading.add_buy_transaction(self.sid, 'SYM_A', '甲', Decimal('10'), 1, '2025-02-01')
        self.trading.add_sell_transaction(t1, Decimal('12'), 1, '2025-02-02')
        ok, t2 = self.trading.add_buy_transaction(self.sid, 'SYM_B', '乙', Decimal('10'), 1, '2025-03-01')
        self.trading.add_sell_transaction(t2, Decimal('9'), 1, '2025-03-10')

        by_symbol = self.analysis.get_strategies_scores_by_symbol('SYM_A')
        self.assertGreaterEqual(len(by_symbol), 1)
        self.assertEqual(by_symbol[0]['stats']['total_trades'], 1)

        # 时间窗口：只包含2025-02期间
        scores_feb = self.analysis.get_strategies_scores_by_time_period('2025-02', 'month')
        # 结果仅包含有交易的策略
        self.assertTrue(all(s['stats']['total_trades'] > 0 for s in scores_feb))


if __name__ == '__main__':
    unittest.main(verbosity=2)


