#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
import os
import sys
from decimal import Decimal
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app
from services import DatabaseService, TradingService, StrategyService, AnalysisService


class TestRoutesDeepFunctional(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()

        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.app.config['DATABASE_PATH'] = self.tmp.name

        self.db = DatabaseService(self.tmp.name)
        self.trading = TradingService(self.db)
        self.strategy = StrategyService(self.db)
        self.analysis = AnalysisService(self.db)

        # inject
        self.app.db_service = self.db
        self.app.trading_service = self.trading
        self.app.strategy_service = self.strategy
        self.app.analysis_service = self.analysis

        self.client = self.app.test_client()

        # base data
        ok, _ = self.strategy.create_strategy('深度A', '')
        ok, _ = self.strategy.create_strategy('深度B', '')
        self.sid_a = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '深度A')
        self.sid_b = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '深度B')

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_trading_delete_restore_permanent_endpoints(self):
        # create trade
        ok, trade_id = self.trading.add_buy_transaction(self.sid_a, 'DDEL', '删股', Decimal('10'), 2, '2025-01-01')
        self.assertTrue(ok)

        # missing confirmation -> 400
        r1 = self.client.post(f'/delete_trade/{trade_id}', data={})
        self.assertEqual(r1.status_code, 400)
        # delete ok
        r2 = self.client.post(f'/delete_trade/{trade_id}', data={'confirmation_code': 'X', 'delete_reason': 't'})
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.get_json().get('success'))

        # restore missing code -> 400
        r3 = self.client.post(f'/restore_trade/{trade_id}', data={})
        self.assertEqual(r3.status_code, 400)
        # restore ok
        r4 = self.client.post(f'/restore_trade/{trade_id}', data={'confirmation_code': 'X'})
        self.assertEqual(r4.status_code, 200)
        self.assertTrue(r4.get_json().get('success'))

        # permanently delete missing fields -> 400
        r5 = self.client.post(f'/permanently_delete_trade/{trade_id}', data={'confirmation_code': 'X'})
        self.assertEqual(r5.status_code, 400)
        # permanently delete ok
        r6 = self.client.post(
            f'/permanently_delete_trade/{trade_id}',
            data={'confirmation_code': 'X', 'confirmation_text': 'CONFIRM', 'delete_reason': 't'}
        )
        self.assertEqual(r6.status_code, 200)
        self.assertTrue(r6.get_json().get('success'))

    def test_analysis_symbol_detail_and_time_variants(self):
        # create trades for symbol detail and periods
        ok, t1 = self.trading.add_buy_transaction(self.sid_a, 'SYMZ', '甲', Decimal('10'), 1, '2025-01-02')
        self.trading.add_sell_transaction(t1, Decimal('11'), 1, '2025-01-03')
        ok, t2 = self.trading.add_buy_transaction(self.sid_b, 'SYMZ', '甲', Decimal('10'), 1, '2025-04-01')
        self.trading.add_sell_transaction(t2, Decimal('9'), 1, '2025-04-10')

        self.assertEqual(self.client.get('/symbol_comparison').status_code, 200)
        # 若无评分数据会跳转回比较页，允许 200 或 302（并跟随后得到200）
        resp = self.client.get('/symbol_detail/SYMZ')
        if resp.status_code == 302:
            resp = self.client.get('/symbol_detail/SYMZ', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # quarter/month pages
        self.assertEqual(self.client.get('/time_comparison?period_type=quarter').status_code, 200)
        self.assertEqual(self.client.get('/time_comparison?period_type=month').status_code, 200)

        # detail for quarter/month
        resp_q1 = self.client.get('/time_detail/2025-Q1')
        if resp_q1.status_code == 302:
            resp_q1 = self.client.get('/time_detail/2025-Q1', follow_redirects=True)
        self.assertEqual(resp_q1.status_code, 200)
        self.assertEqual(self.client.get('/time_detail/2025-01').status_code, 200)

        # deleted trades page
        self.assertEqual(self.client.get('/deleted_trades').status_code, 200)

    def test_api_error_paths_and_trend_exception(self):
        # tag update missing data -> 400
        self.assertEqual(self.client.post('/api/tag/1/update', data={}).status_code, 400)

        # patch trend to raise exception -> expect 500 JSON
        with patch('routes.api_routes.AnalysisService.get_time_periods', side_effect=Exception('boom')):
            r = self.client.get(f'/api/strategy_trend?strategy_id={self.sid_a}&period_type=month')
            self.assertEqual(r.status_code, 500)
            j = r.get_json()
            self.assertFalse(j.get('success'))

    def test_trades_filters_string_strategy_and_misc(self):
        # Non-numeric strategy param, exercises ValueError path
        self.assertEqual(self.client.get('/trades?status=open&strategy=all').status_code, 200)
        self.assertEqual(self.client.get('/trades?status=closed&strategy=name-not-int').status_code, 200)

        # generate confirmation code endpoint
        self.assertEqual(self.client.get('/generate_confirmation_code').status_code, 200)

    def test_add_buy_invalid_strategy_then_valid(self):
        # GET page OK
        self.assertEqual(self.client.get('/add_buy').status_code, 200)
        # POST with non-existing strategy id -> stays on page with error
        r_invalid = self.client.post('/add_buy', data={
            'strategy': 99999,
            'symbol_code': 'X',
            'symbol_name': 'Y',
            'price': '10',
            'quantity': '1',
            'transaction_date': '2025-01-01'
        })
        self.assertEqual(r_invalid.status_code, 200)

        # POST valid
        r_valid = self.client.post('/add_buy', data={
            'strategy': self.sid_a,
            'symbol_code': 'VVV',
            'symbol_name': '名',
            'price': '10',
            'quantity': '1',
            'transaction_date': '2025-01-01'
        })
        self.assertIn(r_valid.status_code, (302, 303))


if __name__ == '__main__':
    unittest.main(verbosity=2)


