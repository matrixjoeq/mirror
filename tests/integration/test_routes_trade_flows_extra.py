#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from decimal import Decimal

from app import create_app


class TestRoutesTradeFlowsExtra(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()
        self.svc = self.app.trading_service
        self.strategy = self.app.strategy_service
        ok, _ = self.strategy.create_strategy('ITF', 'integration extra')
        if not ok:
            pass
        self.sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == 'ITF')

    def tearDown(self):
        self.ctx.pop()

    def test_trade_pages_and_mutations(self):
        # create trade via service to get id
        ok, tid = self.svc.add_buy_transaction('ITF', 'I001', 'I-Stock', Decimal('10.0'), 10, '2025-01-01')
        self.assertTrue(ok)
        ok2, _ = self.svc.add_sell_transaction(tid, Decimal('11.0'), 10, '2025-01-02')
        self.assertTrue(ok2)

        # pages
        self.assertEqual(self.client.get('/trades').status_code, 200)
        self.assertEqual(self.client.get(f'/trade_details/{tid}').status_code, 200)
        self.assertEqual(self.client.get('/add_buy').status_code, 200)
        self.assertEqual(self.client.get(f'/add_sell/{tid}').status_code, 200)

        # delete/restore/permanent via routes
        r_del = self.client.post('/delete_trade/%d' % tid, data={
            'confirmation_code': 'X',
            'delete_reason': 'test',
            'operator_note': 'note'
        })
        self.assertEqual(r_del.status_code, 200)
        r_res = self.client.post('/restore_trade/%d' % tid, data={
            'confirmation_code': 'X',
            'operator_note': 'note'
        })
        self.assertEqual(r_res.status_code, 200)
        r_perm = self.client.post('/permanently_delete_trade/%d' % tid, data={
            'confirmation_code': 'X',
            'confirmation_text': 'CONFIRM',
            'delete_reason': 'test',
            'operator_note': 'note'
        })
        self.assertEqual(r_perm.status_code, 200)


if __name__ == '__main__':
    unittest.main()


