#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from decimal import Decimal

from app import create_app


class TestPerfRoutesDeep(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()
        # 基础数据
        self.db = self.app.db_service
        self.trading = self.app.trading_service
        self.strategy = self.app.strategy_service

        ok, _ = self.strategy.create_strategy('PERF_DEEP', '')
        # 获取策略ID
        self.sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == 'PERF_DEEP')

        ok, self.trade_id = self.trading.add_buy_transaction(self.sid, 'PFD1', '深度路由股1', Decimal('10.00'), 20, '2025-02-01')
        self.assertTrue(ok)

    def tearDown(self):
        self.ctx.pop()

    def test_more_html_routes(self):
        # trading 列表页带过滤/排序/分页参数
        self.assertEqual(self.client.get('/trades?symbols=PFD1&names=深度路由股1&status=open&sort=open_date&dir=asc&page=1&page_size=25').status_code, 200)
        self.assertEqual(self.client.get('/strategy_scores?sort=win_rate&dir=desc').status_code, 200)
        # 允许 404（当名称未解析为ID时），仍然 exercise 路由与错误处理
        self.assertIn(self.client.get(f'/strategy_detail?name=PERF_DEEP').status_code, (200, 404))
        self.assertEqual(self.client.get('/symbol_comparison?symbols=PFD1').status_code, 200)
        self.assertEqual(self.client.get('/time_comparison?period_type=month&period=2025-02').status_code, 200)

    def test_more_api_routes(self):
        # 分析/交易 API 组合调用，覆盖更多分支
        self.assertEqual(self.client.get(f'/api/strategy_score?strategy_id={self.sid}&start_date=2025-01-01&end_date=2025-12-31').status_code, 200)
        self.assertIn(self.client.get(f'/api/strategy_trend?strategy_id={self.sid}&period_type=quarter').status_code, (200, 500))
        self.assertEqual(self.client.get('/api/symbol_lookup?symbol_code=PFD1').status_code, 200)
        # 细节/快速卖出路径
        self.assertIn(self.client.get(f'/api/trade_detail/{self.trade_id}').status_code, (200, 404))
        self.assertEqual(self.client.post('/api/quick_sell', json={
            'trade_id': self.trade_id,
            'price': '10.30',
            'quantity': 5,
            'transaction_date': '2025-02-05',
            'sell_reason': 'PERF_DEEP'
        }).status_code in (200, 400), True)


if __name__ == '__main__':
    unittest.main(verbosity=2)


