#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from app import create_app


class TestQuickSellFunctional(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        # Services
        self.trading_service = self.app.trading_service
        self.strategy_service = self.app.strategy_service

        # Ensure at least one strategy exists and is active
        strategies = self.strategy_service.get_all_strategies()
        if not strategies:
            # Create a default strategy if not present via services directly (name must be unique)
            self.strategy_service.create_strategy('趋势跟踪策略', '用于测试的默认策略')
            strategies = self.strategy_service.get_all_strategies()
        self.strategy_id = strategies[0]['id']
        self.strategy_name = strategies[0]['name']

    def test_trade_detail_endpoint_and_404(self):
        # Create a simple trade with one buy
        ok, tid = self.trading_service.add_buy_transaction(
            strategy=self.strategy_name,
            symbol_code='QSF001',
            symbol_name='快捷卖出测试一',
            price=1.111,
            quantity=10,
            transaction_date='2025-01-01',
            transaction_fee=0,
            buy_reason='test',
        )
        self.assertTrue(ok)
        details = self.trading_service.get_trade_details(tid)
        self.assertGreater(len(details), 0)
        did = details[0]['id']

        # success path
        resp = self.client.get(f'/api/trade_detail/{did}')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['detail']['trade_id'], tid)

        # 404 path
        resp404 = self.client.get('/api/trade_detail/999999')
        self.assertEqual(resp404.status_code, 404)
        data404 = resp404.get_json()
        self.assertFalse(data404['success'])

    def test_quick_sell_success_and_validation(self):
        # Create a trade and perform partial quick sell
        ok, tid = self.trading_service.add_buy_transaction(
            strategy=self.strategy_name,
            symbol_code='QSF002',
            symbol_name='快捷卖出测试二',
            price=2.345,
            quantity=100,
            transaction_date='2025-02-02',
            transaction_fee=0,
        )
        self.assertTrue(ok)

        # success sell 10
        resp = self.client.post('/api/quick_sell', data={
            'trade_id': tid,
            'price': '2.500',
            'transaction_date': '2025-02-03',
            'quantity': 10,
            'transaction_fee': '0.2',
            'sell_reason': 'partial quick sell',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['success'])

        # missing mandatory fields
        resp_bad = self.client.post('/api/quick_sell', data={'trade_id': tid})
        self.assertEqual(resp_bad.status_code, 400)
        self.assertFalse(resp_bad.get_json()['success'])

        # invalid trade_id
        resp_bad2 = self.client.post('/api/quick_sell', data={
            'trade_id': 'abc', 'price': '1.0', 'transaction_date': '2025-02-03', 'quantity': 1,
        })
        self.assertEqual(resp_bad2.status_code, 400)
        self.assertFalse(resp_bad2.get_json()['success'])

        # invalid quantity
        resp_bad3 = self.client.post('/api/quick_sell', data={
            'trade_id': tid, 'price': '1.0', 'transaction_date': '2025-02-03', 'quantity': 0,
        })
        self.assertEqual(resp_bad3.status_code, 400)
        self.assertFalse(resp_bad3.get_json()['success'])

    def test_fifo_remaining_map_and_quick_sell_limit_by_detail(self):
        # Create a trade with two buy lots
        ok, tid = self.trading_service.add_buy_transaction(
            strategy=self.strategy_name,
            symbol_code='QSF_UNIQ_A',
            symbol_name='快捷卖出测试三A',
            price=3.000,
            quantity=10,
            transaction_date='2025-03-01',
            transaction_fee=0,
        )
        self.assertTrue(ok)
        ok2, _ = self.trading_service.add_buy_transaction(
            strategy=self.strategy_name,
            symbol_code='QSF_UNIQ_A',
            symbol_name='快捷卖出测试三A',
            price=3.100,
            quantity=10,
            transaction_date='2025-03-02',
            transaction_fee=0,
        )
        self.assertTrue(ok2)

        details = self.trading_service.get_trade_details(tid)
        buys = [d for d in details if d['transaction_type'] == 'buy']
        self.assertGreaterEqual(len(buys), 2)
        first_buy_id = buys[0]['id']

        # 尝试卖出超过第一笔剩余的份额（应当被接口拒绝）
        resp_over = self.client.post('/api/quick_sell', data={
            'trade_id': tid,
            'price': '3.300',
            'transaction_date': '2025-03-06',
            'quantity': buys[0]['quantity'] + 1,
            'detail_id': first_buy_id,
        })
        self.assertEqual(resp_over.status_code, 400)
        self.assertFalse(resp_over.get_json()['success'])


if __name__ == '__main__':
    unittest.main()


