#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app
from services import DatabaseService, TradingService, StrategyService, AnalysisService


class TestRoutesFunctional(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.app.config['DATABASE_PATH'] = self.temp_db.name

        self.db_service = DatabaseService(self.temp_db.name)
        self.trading_service = TradingService(self.db_service)
        self.strategy_service = StrategyService(self.db_service)
        self.analysis_service = AnalysisService(self.db_service)

        self.app.db_service = self.db_service
        self.app.trading_service = self.trading_service
        self.app.strategy_service = self.strategy_service
        self.app.analysis_service = self.analysis_service

        self.client = self.app.test_client()

        ok, _ = self.strategy_service.create_strategy('功能路由策略', '用于功能路由覆盖')
        self.strategy_id = next(s['id'] for s in self.strategy_service.get_all_strategies() if s['name'] == '功能路由策略')

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_pages_and_api_contracts(self):
        # 页面
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/trades').status_code, 200)
        self.assertEqual(self.client.get('/strategies').status_code, 200)
        self.assertEqual(self.client.get('/strategy_scores').status_code, 200)

        # 买入页与提交
        self.assertEqual(self.client.get('/add_buy').status_code, 200)
        resp = self.client.post('/add_buy', data={
            'strategy': self.strategy_id,
            'symbol_code': 'FNC001',
            'symbol_name': '功能股',
            'price': '10.50',
            'quantity': '100',
            'transaction_date': '2025-01-01',
            'transaction_fee': '0.30',
            'buy_reason': '功能覆盖'
        })
        self.assertEqual(resp.status_code, 302)

        # API: 策略列表
        resp = self.client.get('/api/strategies')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get('success'))

        # API: 标签
        resp = self.client.get('/api/tags')
        self.assertEqual(resp.status_code, 200)

        # API: 评分
        resp = self.client.get(f'/api/strategy_score?strategy_id={self.strategy_id}')
        self.assertEqual(resp.status_code, 200)
        j = resp.get_json()
        self.assertTrue(j.get('success'))
        self.assertIn('stats', j.get('data', {}))

    def test_analysis_pages(self):
        # 标的比较 / 时间比较页面
        self.assertEqual(self.client.get('/symbol_comparison').status_code, 200)
        self.assertEqual(self.client.get('/time_comparison?period_type=year').status_code, 200)
        # 时间段详情（选择存在的年）
        years = self.analysis_service.get_time_periods('year')
        if years:
            self.assertEqual(self.client.get(f'/time_detail/{years[0]}').status_code, 200)


if __name__ == '__main__':
    unittest.main(verbosity=2)


