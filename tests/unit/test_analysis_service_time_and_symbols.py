#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
from decimal import Decimal

from services import DatabaseService, TradingService, StrategyService, AnalysisService


class TestAnalysisServiceTimeAndSymbols(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)
        self.strategy_service = StrategyService(self.db)
        self.trading = TradingService(self.db)
        self.analysis = AnalysisService(self.db)
        ok, _ = self.strategy_service.create_strategy('时间与标的', '')
        self.sid = next(s['id'] for s in self.strategy_service.get_all_strategies() if s['name'] == '时间与标的')

    def test_time_periods_and_scores(self):
        # 创建跨年、跨季度与跨月份的交易（部分闭合）
        # 2024-Q4 月份
        ok, t_dec = self.trading.add_buy_transaction(self.sid, 'TSYM1', 'T1', Decimal('10.00'), 100, '2024-12-20')
        self.assertTrue(ok)
        self.trading.add_sell_transaction(t_dec, Decimal('11.00'), 100, '2024-12-28')

        # 2025-Q1 月份
        ok, t_jan = self.trading.add_buy_transaction(self.sid, 'TSYM2', 'T2', Decimal('10.00'), 100, '2025-01-05')
        self.trading.add_sell_transaction(t_jan, Decimal('12.00'), 100, '2025-01-25')

        # 2025-Q2 月份
        ok, t_apr = self.trading.add_buy_transaction(self.sid, 'TSYM3', 'T3', Decimal('10.00'), 100, '2025-04-10')
        self.trading.add_sell_transaction(t_apr, Decimal('9.50'), 100, '2025-04-20')

        # 年、季度、月份周期列表
        years = self.analysis.get_time_periods('year')
        quarters = self.analysis.get_time_periods('quarter')
        months = self.analysis.get_time_periods('month')
        self.assertIn('2025', years)
        self.assertIn('2024', years)
        self.assertIn('2024-Q4', quarters)
        self.assertIn('2025-Q1', quarters)
        self.assertIn('2025-01', months)
        self.assertIn('2024-12', months)

        # 按时间段评分（年度）
        year_scores = self.analysis.get_strategies_scores_by_time_period('2025', 'year')
        self.assertTrue(any(s['stats']['total_trades'] > 0 for s in year_scores))

        # 时间段汇总
        summary = self.analysis.get_period_summary('2025', 'year')
        self.assertIn('stats', summary)
        self.assertGreaterEqual(summary['stats']['total_trades'], 2)

        # 按标的评分
        symbols = self.analysis.get_all_symbols()
        self.assertGreaterEqual(len(symbols), 3)
        sym_scores = self.analysis.get_strategies_scores_by_symbol('TSYM2')
        # TSYM2 仅有一笔闭合交易
        self.assertTrue(all(s['stats']['total_trades'] >= 1 for s in sym_scores))


if __name__ == '__main__':
    unittest.main(verbosity=2)


