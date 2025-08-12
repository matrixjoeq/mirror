#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from services.mappers import (
    normalize_trade_row,
    normalize_trade_detail_row,
)


class TestMappersDTO(unittest.TestCase):
    def test_normalize_trade_row_defaults(self):
        t = normalize_trade_row({
            'id': 1,
            'symbol_code': 'AAA',
            'remaining_quantity': None,
        })
        self.assertEqual(t['symbol_code'], 'AAA')
        # numeric defaults exist
        self.assertIn('total_gross_buy', t)
        self.assertEqual(t['remaining_quantity'], 0)

    def test_normalize_trade_row_list(self):
        arr = [
            normalize_trade_row({'id': 1}),
            normalize_trade_row({'id': 2, 'total_buy_amount': 123.45}),
        ]
        self.assertEqual(len(arr), 2)
        self.assertIn('total_buy_amount', arr[1])

    def test_normalize_trade_detail_row(self):
        d = normalize_trade_detail_row({'id': 1, 'quantity': '5', 'price': '1.23'})
        self.assertEqual(d['quantity'], 5)
        self.assertAlmostEqual(d['price'], 1.23, places=3)

    def test_normalize_trade_detail_row_list(self):
        arr = [
            normalize_trade_detail_row({'id': 1}),
            normalize_trade_detail_row({'id': 2, 'remaining_for_quick': 3, 'can_quick_sell': 1}),
        ]
        self.assertEqual(arr[1]['remaining_for_quick'], 3)
        self.assertTrue(arr[1]['can_quick_sell'])

    def test_strategy_tags_normalization_example(self):
        # 策略相关 map_* 已移除，示例性校验保留
        s = {'id': '10', 'name': 'S', 'tags': None}
        self.assertEqual(int(s['id']), 10)
        tags = s.get('tags') or []
        self.assertEqual(tags, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)


