#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.analysis_service import AnalysisService
from services.database_service import DatabaseService


class TestAnalysisServiceMetricsFallback(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_analysis_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = AnalysisService(self.db)

        # 基础策略与一笔交易（不关注数值，只为形成评分输入集）
        self.db.execute_transaction([
            {
                'query': "INSERT INTO strategies (name) VALUES (?)",
                'params': ("策略一",),
            },
            {
                'query': (
                    "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted) "
                    "VALUES (?, ?, ?, ?, ?, ?, 0)"
                ),
                'params': (1, "策略一", "AAA", "Alpha", "2024-01-01", "open"),
            },
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_calculate_strategy_score_advanced_metrics_exception_fallback(self):
        # 强制高级指标抛异常，检查回退为 0.0
        def boom(*args, **kwargs):
            raise RuntimeError("boom")

        self.svc._compute_advanced_metrics = boom  # type: ignore[attr-defined]
        result = self.svc.calculate_strategy_score(strategy_id=1)
        stats = result['stats']
        self.assertIn('annual_volatility', stats)
        self.assertIn('annual_return', stats)
        self.assertIn('max_drawdown', stats)
        self.assertIn('sharpe_ratio', stats)
        self.assertIn('calmar_ratio', stats)
        self.assertEqual(stats['annual_volatility'], 0.0)
        self.assertEqual(stats['annual_return'], 0.0)
        self.assertEqual(stats['max_drawdown'], 0.0)
        self.assertEqual(stats['sharpe_ratio'], 0.0)
        self.assertEqual(stats['calmar_ratio'], 0.0)

    def test_compute_score_fields_boundaries(self):
        # 覆盖 _compute_legacy_fields 的主要分支
        s1 = self.svc.compute_score_fields({'win_rate': 100.0, 'avg_profit_loss_ratio': 10.0, 'total_trades': 10, 'avg_holding_days': 1})
        self.assertGreaterEqual(s1['total_score'], 23)  # 高档

        s2 = self.svc.compute_score_fields({'win_rate': 90.0, 'avg_profit_loss_ratio': 9.0, 'total_trades': 10, 'avg_holding_days': 5})
        self.assertTrue(23 <= s2['total_score'] < 26)  # A 档

        # B 档：总分在 [20, 23)
        s3 = self.svc.compute_score_fields({'win_rate': 90.0, 'avg_profit_loss_ratio': 6.0, 'total_trades': 10, 'avg_holding_days': 10})
        self.assertTrue(20 <= s3['total_score'] < 23)

        # C 档：总分在 [18, 20)
        s4 = self.svc.compute_score_fields({'win_rate': 80.0, 'avg_profit_loss_ratio': 4.0, 'total_trades': 10, 'avg_holding_days': 30})
        self.assertTrue(18 <= s4['total_score'] < 20)

        s5 = self.svc.compute_score_fields({'win_rate': 0.0, 'avg_profit_loss_ratio': 0.0, 'total_trades': 0, 'avg_holding_days': 999})
        self.assertLess(s5['total_score'], 18)  # D 档


if __name__ == '__main__':
    unittest.main()


