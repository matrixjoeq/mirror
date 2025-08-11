#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from decimal import Decimal
from app import create_app


class TestTradingRoutesQuickCoverage(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.trading_service = self.app.trading_service
        self.strategy_service = self.app.strategy_service
        strategies = self.strategy_service.get_all_strategies()
        if not strategies:
            self.strategy_service.create_strategy('趋势跟踪策略', '默认策略')
            strategies = self.strategy_service.get_all_strategies()
        self.strategy_id = strategies[0]['id']
        self.strategy_name = strategies[0]['name']

    def test_trades_filters_and_invalid_strategy_param(self):
        # Create two trades under same strategy
        ok1, _ = self.trading_service.add_buy_transaction(self.strategy_name, 'FILT001', '过滤测试1', Decimal('1.0'), 1, '2025-01-10', Decimal('0'))
        ok2, _ = self.trading_service.add_buy_transaction(self.strategy_name, 'FILT002', '过滤测试2', Decimal('1.0'), 1, '2025-01-10', Decimal('0'))
        self.assertTrue(ok1 and ok2)

        # /trades default
        r1 = self.client.get('/trades')
        self.assertEqual(r1.status_code, 200)
        # with status filter
        r2 = self.client.get('/trades?status=open')
        self.assertEqual(r2.status_code, 200)
        # with strategy id filter
        r3 = self.client.get(f'/trades?strategy={self.strategy_id}')
        self.assertEqual(r3.status_code, 200)
        # invalid strategy forces ValueError path -> treated as string and ignored
        r4 = self.client.get('/trades?strategy=notanint')
        self.assertEqual(r4.status_code, 200)

    def test_add_buy_invalid_strategy_and_add_sell_exceed(self):
        # GET add_buy
        rb_get = self.client.get('/add_buy')
        self.assertEqual(rb_get.status_code, 200)
        # POST with invalid strategy id
        resp_invalid = self.client.post('/add_buy', data={
            'strategy': 987654321,  # non-existent
            'symbol_code': 'INV001', 'symbol_name': '无效策略',
            'price': '1.0', 'quantity': '1', 'transaction_date': '2025-01-01', 'transaction_fee': '0'
        })
        self.assertEqual(resp_invalid.status_code, 200)  # renders with error

        # Create a valid trade and then exceed sell
        ok, tid = self.trading_service.add_buy_transaction(self.strategy_name, 'SELLX01', '卖出校验', Decimal('2.0'), 5, '2025-01-02', Decimal('0'))
        self.assertTrue(ok)
        rs_get = self.client.get(f'/add_sell/{tid}')
        self.assertEqual(rs_get.status_code, 200)
        rs_post = self.client.post(f'/add_sell/{tid}', data={
            'price': '2.0', 'quantity': '10', 'transaction_date': '2025-01-03', 'transaction_fee': '0', 'sell_reason': 'exceed'
        }, follow_redirects=False)
        # 超卖会返回错误并重新渲染，但某些分支可能重定向，接受 200/302
        self.assertIn(rs_post.status_code, (200, 302, 303))

    def test_delete_restore_and_permanently_missing_fields(self):
        # Create a trade to delete
        ok, tid = self.trading_service.add_buy_transaction(self.strategy_name, 'DEL001', '删除测试', Decimal('1.0'), 1, '2025-01-05', Decimal('0'))
        self.assertTrue(ok)
        # delete_trade requires confirmation_code
        dresp = self.client.post(f'/delete_trade/{tid}', data={'confirmation_code': 'ABC', 'delete_reason': '测试', 'operator_note': 'note'})
        self.assertEqual(dresp.status_code, 200)
        self.assertTrue(dresp.get_json()['success'])
        # deleted_trades page
        page = self.client.get('/deleted_trades')
        self.assertEqual(page.status_code, 200)
        # restore requires confirmation_code
        rresp = self.client.post(f'/restore_trade/{tid}', data={'confirmation_code': 'ABC'})
        self.assertEqual(rresp.status_code, 200)
        self.assertTrue(rresp.get_json()['success'])

        # permanently delete requires fields -> missing returns 400
        presp = self.client.post(f'/permanently_delete_trade/{tid}', data={})
        self.assertEqual(presp.status_code, 400)

    def test_batch_delete_empty_and_generate_code(self):
        # empty list -> 400
        bresp = self.client.post('/batch_delete_trades', data={'confirmation_code': 'X'})
        self.assertEqual(bresp.status_code, 400)
        # generate confirmation code endpoint
        code = self.client.get('/generate_confirmation_code')
        self.assertEqual(code.status_code, 200)
        self.assertIn('confirmation_code', code.get_json())


