#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
from decimal import Decimal

from services import DatabaseService, TradingService, StrategyService, AnalysisService


class TestAnalysisServiceMore(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = DatabaseService(self.temp_db.name)
        self.strategy_service = StrategyService(self.db)
        self.trading = TradingService(self.db)
        self.analysis = AnalysisService(self.db)
        ok, _ = self.strategy_service.create_strategy('分析扩展', '')
        self.sid = next(s['id'] for s in self.strategy_service.get_all_strategies() if s['name'] == '分析扩展')

    def test_time_window_and_symbol_filter(self):
        # 两笔闭合交易：一笔在窗口内，一笔在窗口外
        ok, t1 = self.trading.add_buy_transaction(self.sid, 'SYM1', '一号', Decimal('10.00'), 100, '2025-01-05')
        self.assertTrue(ok)
        self.trading.add_sell_transaction(t1, Decimal('11.00'), 100, '2025-01-10')

        ok, t2 = self.trading.add_buy_transaction(self.sid, 'SYM2', '二号', Decimal('10.00'), 100, '2024-12-01')
        self.assertTrue(ok)
        self.trading.add_sell_transaction(t2, Decimal('12.00'), 100, '2024-12-10')

        # 仅统计 2025 年 1 月内
        score = self.analysis.calculate_strategy_score(strategy_id=self.sid, start_date='2025-01-01', end_date='2025-01-31')
        self.assertEqual(score['stats']['total_trades'], 1)

        # 仅统计特定标的
        score_sym2 = self.analysis.calculate_strategy_score(strategy_id=self.sid, symbol_code='SYM2')
        self.assertEqual(score_sym2['stats']['total_trades'], 1)

    def test_profit_factor_edge_cases(self):
        # 仅盈利（PF 视为 9999.0）
        ok, t1 = self.trading.add_buy_transaction(self.sid, 'PONLY', '仅盈', Decimal('10.00'), 100, '2025-01-01')
        self.trading.add_sell_transaction(t1, Decimal('12.00'), 100, '2025-01-02')
        pf_only = self.analysis.calculate_strategy_score(strategy_id=self.sid)
        self.assertEqual(pf_only['stats']['avg_profit_loss_ratio'], 9999.0)
        self.assertEqual(pf_only['stats']['win_rate'], 100.0)

        # 仅亏损（PF=0）
        ok, t2 = self.trading.add_buy_transaction(self.sid, 'LONLY', '仅亏', Decimal('10.00'), 100, '2025-01-03')
        self.trading.add_sell_transaction(t2, Decimal('9.00'), 100, '2025-01-04')
        pf_mix = self.analysis.calculate_strategy_score(strategy_id=self.sid)
        # PF 混合含前面的盈利和本次亏损，应为有限数值
        self.assertGreater(pf_mix['stats']['avg_profit_loss_ratio'], 0.0)

    def test_compute_score_fields_variants(self):
        svc = AnalysisService(self.db)
        # empty stats
        out = svc.compute_score_fields({})
        self.assertEqual(out['total_score'], 0.0)
        self.assertEqual(out['rating'], 'D')
        # perfect
        out = svc.compute_score_fields({'win_rate': 100, 'avg_profit_loss_ratio': 9999.0, 'total_trades': 10, 'avg_holding_days': 1})
        self.assertGreaterEqual(out['win_rate_score'], 10.0)
        self.assertEqual(out['profit_loss_ratio_score'], 10.0)
        self.assertEqual(out['frequency_score'], 8.0)
        self.assertGreaterEqual(out['total_score'], 26.0)
        self.assertEqual(out['rating'], 'A+')
        # moderate
        out = svc.compute_score_fields({'win_rate': 55, 'avg_profit_loss_ratio': 2.5, 'total_trades': 5, 'avg_holding_days': 10})
        self.assertAlmostEqual(out['win_rate_score'], 5.5, places=1)
        self.assertAlmostEqual(out['profit_loss_ratio_score'], 2.5, places=1)
        self.assertEqual(out['frequency_score'], 6.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)


