#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from typing import Any, Optional, Tuple

from services.analysis_service import AnalysisService


class _FakeDb:
    def execute_query(self, query: str, params: Optional[Tuple[Any, ...]] = None, fetch_one: bool = False, fetch_all: bool = True):
        # 默认返回空，使 calculate_strategy_score 走空集路径
        return None if fetch_one else []


class TestAnalysisServiceLegacyFields(unittest.TestCase):
    def setUp(self):
        self.svc = AnalysisService(_FakeDb())

    def test_compute_legacy_fields_basic(self):
        stats = {
            'win_rate': 60.0,
            'avg_profit_loss_ratio': 2.5,
            'avg_holding_days': 5,
            'total_trades': 10,
        }
        fields = self.svc._compute_legacy_fields(stats)
        self.assertGreaterEqual(fields['win_rate_score'], 0)
        self.assertGreaterEqual(fields['profit_loss_ratio_score'], 0)
        self.assertGreaterEqual(fields['frequency_score'], 0)
        self.assertGreaterEqual(fields['total_score'], 0)
        self.assertIn(fields['rating'], ['A+', 'A', 'B', 'C', 'D'])

    def test_compute_legacy_fields_zero_trades(self):
        stats = {
            'win_rate': 0.0,
            'avg_profit_loss_ratio': 0.0,
            'avg_holding_days': 0.0,
            'total_trades': 0,
        }
        fields = self.svc._compute_legacy_fields(stats)
        self.assertEqual(fields['win_rate_score'], 0.0)
        self.assertEqual(fields['profit_loss_ratio_score'], 0.0)
        self.assertEqual(fields['frequency_score'], 0.0)
        self.assertEqual(fields['rating'], 'D')

    def test_calculate_strategy_score_return_dto_and_apply_legacy(self):
        dto = self.svc.calculate_strategy_score(return_dto=True)
        d = {'stats': {'win_rate': 50.0, 'avg_profit_loss_ratio': 1.5, 'avg_holding_days': 10, 'total_trades': 2}}
        # 模拟填充值
        d.update(self.svc._compute_legacy_fields(d['stats']))
        self.assertIn('total_score', d)
        self.assertIn('rating', d)


if __name__ == '__main__':
    unittest.main(verbosity=2)


