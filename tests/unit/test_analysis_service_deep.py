#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
from decimal import Decimal

from services import DatabaseService, TradingService, StrategyService, AnalysisService


class TestAnalysisServiceDeep(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)
        self.strategy_service = StrategyService(self.db)
        self.trading = TradingService(self.db)
        self.analysis = AnalysisService(self.db)

    def test_no_trades_returns_zero(self):
        # 新策略无交易
        ok, _ = self.strategy_service.create_strategy('空策略', '')
        sid = next(s['id'] for s in self.strategy_service.get_all_strategies() if s['name'] == '空策略')
        score = self.analysis.calculate_strategy_score(strategy_id=sid)
        stats = score['stats']
        self.assertEqual(stats['total_trades'], 0)
        self.assertEqual(stats['win_rate'], 0)
        self.assertEqual(stats['total_investment'], 0)
        self.assertEqual(stats['total_return'], 0)
        self.assertEqual(stats['total_fees'], 0)

    def test_strategy_name_resolution_and_filters_and_fees(self):
        ok, _ = self.strategy_service.create_strategy('按名策略', '')
        # 通过名称解析
        by_name = '按名策略'
        sid = next(s['id'] for s in self.strategy_service.get_all_strategies() if s['name'] == by_name)

        # 两笔交易不同标的与日期
        ok, t1 = self.trading.add_buy_transaction(sid, 'BY1', '一号', Decimal('10.00'), 100, '2025-01-05', Decimal('1.00'))
        self.trading.add_sell_transaction(t1, Decimal('12.00'), 100, '2025-01-10', Decimal('0.50'))

        ok, t2 = self.trading.add_buy_transaction(sid, 'BY2', '二号', Decimal('8.00'), 50, '2025-02-01', Decimal('0.40'))
        self.trading.add_sell_transaction(t2, Decimal('7.50'), 50, '2025-02-05', Decimal('0.25'))

        # 仅统计指定标的 + 时间窗口
        score = self.analysis.calculate_strategy_score(strategy=by_name, symbol_code='BY1', start_date='2025-01-01', end_date='2025-01-31')
        stats = score['stats']
        self.assertEqual(stats['total_trades'], 1)
        # 费用为买入1.00 + 卖出0.50
        self.assertAlmostEqual(stats['total_fees'], 1.50, places=2)

    def test_get_time_periods_and_scores_sorting(self):
        ok, _ = self.strategy_service.create_strategy('A策略', '')
        ok, _ = self.strategy_service.create_strategy('B策略', '')
        strategies = self.strategy_service.get_all_strategies()
        sid_a = next(s['id'] for s in strategies if s['name'] == 'A策略')
        sid_b = next(s['id'] for s in strategies if s['name'] == 'B策略')

        # A策略盈利
        ok, ta = self.trading.add_buy_transaction(sid_a, 'SA', 'A', Decimal('10.00'), 100, '2025-03-01')
        self.trading.add_sell_transaction(ta, Decimal('12.00'), 100, '2025-03-10')
        # B策略亏损
        ok, tb = self.trading.add_buy_transaction(sid_b, 'SB', 'B', Decimal('10.00'), 100, '2025-03-01')
        self.trading.add_sell_transaction(tb, Decimal('9.00'), 100, '2025-03-10')

        # 年/季/月有值
        years = self.analysis.get_time_periods('year')
        quarters = self.analysis.get_time_periods('quarter')
        months = self.analysis.get_time_periods('month')
        self.assertIn('2025', years)
        self.assertTrue(any(q.endswith('Q1') for q in quarters))
        self.assertIn('2025-03', months)

        # get_strategy_scores 应按总收益率降序排序（A在前）
        scores = self.analysis.get_strategy_scores()
        ids = [s['strategy_id'] for s in scores]
        self.assertLess(ids.index(sid_a), ids.index(sid_b))

        # 按时间段
        period_scores = self.analysis.get_strategies_scores_by_time_period('2025', 'year')
        self.assertTrue(any(s['strategy_id'] == sid_a for s in period_scores))
        self.assertTrue(any(s['strategy_id'] == sid_b for s in period_scores))

    def test_get_all_symbols_and_by_symbol(self):
        ok, _ = self.strategy_service.create_strategy('S策略', '')
        sid = next(s['id'] for s in self.strategy_service.get_all_strategies() if s['name'] == 'S策略')
        ok, t1 = self.trading.add_buy_transaction(sid, 'SYM_A', 'A', Decimal('10.00'), 100, '2025-04-01')
        self.trading.add_sell_transaction(t1, Decimal('11.00'), 100, '2025-04-05')

        symbols = self.analysis.get_all_symbols()
        self.assertTrue(any(s['symbol_code'] == 'SYM_A' for s in symbols))

        by_symbol = self.analysis.get_strategies_scores_by_symbol('SYM_A')
        self.assertTrue(all(s['stats']['total_trades'] > 0 for s in by_symbol))


if __name__ == '__main__':
    unittest.main(verbosity=2)


