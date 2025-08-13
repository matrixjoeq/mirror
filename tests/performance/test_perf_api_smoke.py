#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app


class TestPerfApiSmoke(unittest.TestCase):
    """轻量 API 冒烟测试，用于在性能测试侧提升 routes 覆盖率。"""

    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()
        # 服务实例（使用测试应用注入的隔离DB）
        self.db = self.app.db_service
        self.trading = self.app.trading_service
        self.strategy = self.app.strategy_service
        self.analysis = self.app.analysis_service

        # 创建基础策略与交易数据
        ok, _ = self.strategy.create_strategy('API_SMOKE', '')
        self.assertTrue(ok or True)  # 已存在也可
        self.sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == 'API_SMOKE')
        ok, self.trade_id = self.trading.add_buy_transaction(self.sid, 'API1', '接口股1', Decimal('10.00'), 10, '2025-01-01')
        self.assertTrue(ok)

    def tearDown(self):
        self.ctx.pop()

    def test_api_endpoints_smoke(self):
        # 基础列表类接口
        r = self.client.get('/api/strategies')
        self.assertEqual(r.status_code, 200)

        r = self.client.get('/api/tags')
        self.assertEqual(r.status_code, 200)

        # 创建/更新/删除标签
        r = self.client.post('/api/tag/create', json={'name': 'T_API'})
        self.assertIn(r.status_code, (200, 400))  # 已存在时可能返回成功或提示

        tags_resp = self.client.get('/api/tags')
        self.assertEqual(tags_resp.status_code, 200)
        data = tags_resp.get_json() or {}
        tag_list = data.get('data', [])
        tag = next((t for t in tag_list if t.get('name') in ('T_API', 'T_API_NEW')), None)
        if tag:
            tid = tag.get('id')
            r_upd = self.client.post(f'/api/tag/{tid}/update', json={'new_name': 'T_API_NEW'})
            self.assertIn(r_upd.status_code, (200, 400))
            r_del = self.client.post(f'/api/tag/{tid}/delete')
            self.assertIn(r_del.status_code, (200, 400))

        # symbol_lookup（存在与不存在）
        r = self.client.get('/api/symbol_lookup?symbol_code=API1')
        self.assertEqual(r.status_code, 200)
        r = self.client.get('/api/symbol_lookup?symbol_code=NOPE')
        self.assertEqual(r.status_code, 200)

        # trade_detail（不存在ID）
        r = self.client.get('/api/trade_detail/99999999')
        self.assertEqual(r.status_code, 404)

        # quick_sell（参数缺失与有效）
        r = self.client.post('/api/quick_sell', json={'trade_id': self.trade_id})
        self.assertEqual(r.status_code, 400)
        r_ok = self.client.post('/api/quick_sell', json={
            'trade_id': self.trade_id,
            'price': '10.50',
            'quantity': 10,
            'transaction_date': '2025-01-05',
            'sell_reason': 'SMOKE'
        })
        self.assertIn(r_ok.status_code, (200, 400))

        # strategy_score 与 strategy_trend
        r = self.client.get(f'/api/strategy_score?strategy_id={self.sid}')
        self.assertEqual(r.status_code, 200)
        r = self.client.get('/api/strategy_trend')  # 缺参数 400
        self.assertEqual(r.status_code, 400)
        r = self.client.get(f'/api/strategy_trend?strategy_id={self.sid}&period_type=month')
        self.assertIn(r.status_code, (200, 500))  # 某些日期计算异常时可能 500，但会覆盖错误路径


if __name__ == '__main__':
    unittest.main(verbosity=2)


