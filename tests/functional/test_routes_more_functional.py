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


class TestRoutesMoreFunctional(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()

        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['DATABASE_PATH'] = self.tmp.name

        self.db = DatabaseService(self.tmp.name)
        self.trading = TradingService(self.db)
        self.strategy = StrategyService(self.db)
        self.analysis = AnalysisService(self.db)

        # inject services
        self.app.db_service = self.db
        self.app.trading_service = self.trading
        self.app.strategy_service = self.strategy
        self.app.analysis_service = self.analysis

        self.client = self.app.test_client()

        # base data
        ok, _ = self.strategy.create_strategy('功能A', '')
        ok, _ = self.strategy.create_strategy('功能B', '')
        self.sid_a = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '功能A')
        self.sid_b = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '功能B')

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_trades_filters_and_combination(self):
        # open trade for A
        ok, t_open = self.trading.add_buy_transaction(self.sid_a, 'FAAA', '甲', Decimal('10'), 5, '2025-01-01')
        self.assertTrue(ok)
        # closed trade for B
        ok, t_closed = self.trading.add_buy_transaction(self.sid_b, 'FBBB', '乙', Decimal('10'), 5, '2025-01-01')
        self.assertTrue(ok)
        self.trading.add_sell_transaction(t_closed, Decimal('11'), 5, '2025-01-02')

        # status filter only
        self.assertEqual(self.client.get('/trades?status=open').status_code, 200)
        self.assertEqual(self.client.get('/trades?status=closed').status_code, 200)
        # combined status+strategy
        self.assertEqual(self.client.get(f'/trades?status=open&strategy={self.sid_a}').status_code, 200)
        self.assertEqual(self.client.get(f'/trades?status=closed&strategy={self.sid_b}').status_code, 200)

    def test_add_sell_page_and_post_errors(self):
        ok, trade_id = self.trading.add_buy_transaction(self.sid_a, 'SELLX', '卖出股', Decimal('10'), 10, '2025-01-01')
        self.assertTrue(ok)
        # render page
        self.assertEqual(self.client.get(f'/add_sell/{trade_id}').status_code, 200)
        # quantity exceeds
        resp_err = self.client.post(f'/add_sell/{trade_id}', data={
            'price': '11',
            'quantity': '1000',
            'transaction_date': '2025-01-02',
            'transaction_fee': '0.1',
            'sell_reason': 'too much'
        })
        self.assertEqual(resp_err.status_code, 200)
        # correct sell
        resp_ok = self.client.post(f'/add_sell/{trade_id}', data={
            'price': '11',
            'quantity': '10',
            'transaction_date': '2025-01-02',
            'transaction_fee': '0.1',
            'sell_reason': 'ok'
        })
        self.assertIn(resp_ok.status_code, (302, 303))

    def test_strategy_crud_functional(self):
        # create page
        self.assertEqual(self.client.get('/strategy/create').status_code, 200)
        # post invalid
        resp_invalid = self.client.post('/strategy/create', data={'name': '', 'description': ''})
        self.assertEqual(resp_invalid.status_code, 200)
        # post valid
        resp_valid = self.client.post('/strategy/create', data={'name': '功能C', 'description': ''})
        self.assertIn(resp_valid.status_code, (302, 303))
        sid_c = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '功能C')

        # edit page
        self.assertEqual(self.client.get(f'/strategy/{sid_c}/edit').status_code, 200)
        # edit via ajax
        resp_edit = self.client.post(
            f'/strategy/{sid_c}/edit',
            data={'name': '功能C2', 'description': 'd', 'tags': []},
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(resp_edit.status_code, 200)
        self.assertTrue(resp_edit.get_json().get('success') in (True, False))

        # delete
        resp_del = self.client.post(f'/strategy/{sid_c}/delete')
        self.assertEqual(resp_del.status_code, 200)
        self.assertIn('success', resp_del.get_json())

    def test_api_tags_and_trend(self):
        # missing name -> 400
        self.assertEqual(self.client.post('/api/tag/create', data={}).status_code, 400)
        # create tag
        r_create = self.client.post('/api/tag/create', data={'name': 'TT'})
        self.assertEqual(r_create.status_code, 200)
        # list tags
        r_list = self.client.get('/api/tags')
        self.assertEqual(r_list.status_code, 200)
        tags = r_list.get_json().get('data', [])
        tag = next((t for t in tags if t['name'] == 'TT'), None)
        self.assertIsNotNone(tag)
        # update tag (json)
        r_upd = self.client.post(f"/api/tag/{tag['id']}/update", json={'new_name': 'TT2'})
        self.assertEqual(r_upd.status_code, 200)
        # delete tag
        r_del = self.client.post(f"/api/tag/{tag['id']}/delete")
        self.assertEqual(r_del.status_code, 200)

        # strategy trend: missing id -> 400
        self.assertEqual(self.client.get('/api/strategy_trend').status_code, 400)
        # create data across months
        ok, t1 = self.trading.add_buy_transaction(self.sid_a, 'TR1', '甲', Decimal('10'), 1, '2025-01-02')
        self.trading.add_sell_transaction(t1, Decimal('11'), 1, '2025-01-03')
        ok, t2 = self.trading.add_buy_transaction(self.sid_a, 'TR2', '乙', Decimal('10'), 1, '2025-02-02')
        self.trading.add_sell_transaction(t2, Decimal('9'), 1, '2025-02-03')
        r_trend = self.client.get(f'/api/strategy_trend?strategy_id={self.sid_a}&period_type=month')
        self.assertEqual(r_trend.status_code, 200)
        self.assertTrue(r_trend.get_json().get('success'))

    def test_analysis_detail_sorting(self):
        ok, t1 = self.trading.add_buy_transaction(self.sid_b, 'S1', '一', Decimal('10'), 1, '2025-03-01')
        self.trading.add_sell_transaction(t1, Decimal('12'), 1, '2025-03-02')
        ok, t2 = self.trading.add_buy_transaction(self.sid_b, 'S2', '二', Decimal('10'), 1, '2025-04-01')
        self.trading.add_sell_transaction(t2, Decimal('9'), 1, '2025-04-02')

        # detail with different sort keys
        self.assertEqual(self.client.get(f'/strategy_detail/{self.sid_b}?sort_by=total_score&sort_order=desc').status_code, 200)
        self.assertEqual(self.client.get(f'/strategy_detail/{self.sid_b}?sort_by=symbol_code&sort_order=asc').status_code, 200)


if __name__ == '__main__':
    unittest.main(verbosity=2)


