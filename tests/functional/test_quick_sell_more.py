#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from app import create_app


class TestQuickSellMoreFunctional(unittest.TestCase):
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

    def test_symbol_lookup_found_and_not_found(self):
        # prepare a trade so symbol exists
        ok, tid = self.trading_service.add_buy_transaction(
            strategy=self.strategy_name,
            symbol_code='LOOKUP01',
            symbol_name='查询存在测试',
            price=1.0,
            quantity=1,
            transaction_date='2025-01-01',
            transaction_fee=0,
        )
        self.assertTrue(ok)
        r1 = self.client.get('/api/symbol_lookup?symbol_code=LOOKUP01')
        self.assertEqual(r1.status_code, 200)
        j1 = r1.get_json()
        self.assertTrue(j1['success'])
        self.assertTrue(j1['found'])
        self.assertEqual(j1['data']['symbol_name'], '查询存在测试')

        r2 = self.client.get('/api/symbol_lookup?symbol_code=NOTEXIST01')
        self.assertEqual(r2.status_code, 200)
        j2 = r2.get_json()
        self.assertTrue(j2['success'])
        self.assertFalse(j2['found'])

    def test_quick_sell_validation_missing_fields(self):
        # missing price/date
        resp = self.client.post('/api/quick_sell', data={'trade_id': 999})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()['success'])

        # invalid trade_id
        resp2 = self.client.post('/api/quick_sell', data={'trade_id': 'x', 'price': '1', 'transaction_date': '2025-01-01', 'quantity': 1})
        self.assertEqual(resp2.status_code, 400)
        self.assertFalse(resp2.get_json()['success'])

        # invalid quantity
        # we need a real trade_id to pass basic checks
        ok, tid = self.trading_service.add_buy_transaction(
            strategy=self.strategy_name,
            symbol_code='QSVAL01',
            symbol_name='校验测试',
            price=1.0,
            quantity=1,
            transaction_date='2025-01-02',
            transaction_fee=0,
        )
        self.assertTrue(ok)
        resp3 = self.client.post('/api/quick_sell', data={'trade_id': tid, 'price': '1', 'transaction_date': '2025-01-02', 'quantity': 0})
        self.assertEqual(resp3.status_code, 400)
        self.assertFalse(resp3.get_json()['success'])


