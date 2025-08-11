#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from decimal import Decimal
from app import create_app


class TestTradingRoutesMoreQuick(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.trading_service = self.app.trading_service
        self.strategy_service = self.app.strategy_service
        strategies = self.strategy_service.get_all_strategies()
        if not strategies:
            self.strategy_service.create_strategy('趋势跟踪策略', '默认策略')
            strategies = self.strategy_service.get_all_strategies()
        self.strategy_name = strategies[0]['name']

    def test_add_sell_close_and_edit_post_redirect(self):
        ok, tid = self.trading_service.add_buy_transaction(
            self.strategy_name, 'CLS001', '关闭测试', Decimal('2.0'), 5, '2025-01-08', Decimal('0')
        )
        self.assertTrue(ok)
        r_get = self.client.get(f'/add_sell/{tid}')
        self.assertEqual(r_get.status_code, 200)
        r_post = self.client.post(
            f'/add_sell/{tid}',
            data={'price': '2.5', 'quantity': '5', 'transaction_date': '2025-01-09', 'transaction_fee': '0', 'sell_reason': 'close'},
            follow_redirects=False,
        )
        # 成功后重定向至 /trades
        self.assertIn(r_post.status_code, (302, 303))

        # edit_trade GET 与 POST（POST重定向）
        r_edit_get = self.client.get(f'/edit_trade/{tid}')
        self.assertEqual(r_edit_get.status_code, 200)
        r_edit_post = self.client.post(f'/edit_trade/{tid}', data={'noop': '1'}, follow_redirects=False)
        self.assertIn(r_edit_post.status_code, (302, 303))

    def test_trade_details_invalid_redirect(self):
        r = self.client.get('/trade_details/999999', follow_redirects=False)
        self.assertIn(r.status_code, (302, 303))

    def test_batch_delete_restore_and_permanent_success(self):
        # prepare two trades
        ok1, t1 = self.trading_service.add_buy_transaction(self.strategy_name, 'BDEL01', '批量删', Decimal('1'), 1, '2025-01-11', Decimal('0'))
        ok2, t2 = self.trading_service.add_buy_transaction(self.strategy_name, 'BDEL02', '批量删2', Decimal('1'), 1, '2025-01-11', Decimal('0'))
        self.assertTrue(ok1 and ok2)

        # batch delete
        resp_del = self.client.post('/batch_delete_trades', data={
            'trade_ids[]': [t1, t2],
            'confirmation_code': 'ABC',
            'delete_reason': '测试',
            'operator_note': 'note'
        })
        self.assertEqual(resp_del.status_code, 200)
        self.assertTrue(resp_del.get_json()['success'])

        # deleted_trades page
        page = self.client.get('/deleted_trades')
        self.assertEqual(page.status_code, 200)

        # batch restore
        resp_res = self.client.post('/batch_restore_trades', data={
            'trade_ids[]': [t1, t2],
            'confirmation_code': 'ABC',
            'operator_note': 'note'
        })
        self.assertEqual(resp_res.status_code, 200)
        self.assertTrue(resp_res.get_json()['success'])

        # permanently delete a single trade success path
        resp_perm = self.client.post(f'/permanently_delete_trade/{t1}', data={
            'confirmation_code': 'XYZ',
            'confirmation_text': 'PERMANENTLY DELETE',
            'delete_reason': '测试',
            'operator_note': 'note'
        })
        self.assertEqual(resp_perm.status_code, 200)
        self.assertTrue(resp_perm.get_json()['success'])


