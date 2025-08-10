#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app
from services import DatabaseService, StrategyService


class TestAnalysisPagesEdges(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['DATABASE_PATH'] = self.tmp.name
        self.db = DatabaseService(self.tmp.name)
        self.app.db_service = self.db
        self.client = self.app.test_client()

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_pages_on_empty_data(self):
        # 无任何数据时的页面加载
        self.assertEqual(self.client.get('/strategy_scores').status_code, 200)
        self.assertEqual(self.client.get('/symbol_comparison').status_code, 200)
        # time comparison invalid type falls back to year
        self.assertEqual(self.client.get('/time_comparison?period_type=invalid').status_code, 200)
        # 任意period detail在空库也应能渲染页面
        self.assertEqual(self.client.get('/time_detail/2025').status_code, 200)

    def test_strategy_detail_without_closed_trades(self):
        # 仅创建策略但没有交易
        strategy_service = StrategyService(self.db)
        ok, _ = strategy_service.create_strategy('功能空策略', '')
        sid = next(s['id'] for s in strategy_service.get_all_strategies() if s['name'] == '功能空策略')
        self.assertEqual(self.client.get(f'/strategy_detail/{sid}').status_code, 200)


if __name__ == '__main__':
    unittest.main(verbosity=2)


