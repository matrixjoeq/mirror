#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from services.mappers import map_trade_row_to_model, map_detail_row_to_model, to_dict_dataclass


class TestMappers(unittest.TestCase):
    def test_map_trade(self):
        row = {
            'id': 1,
            'strategy_id': 2,
            'symbol_code': 'ABC',
            'symbol_name': '名称',
            'status': 'open',
            'total_buy_amount': 100.5,
        }
        t = map_trade_row_to_model(row)
        self.assertEqual(t.id, 1)
        d = to_dict_dataclass(t)
        self.assertEqual(d['symbol_code'], 'ABC')

    def test_map_detail(self):
        row = {
            'id': 10,
            'trade_id': 1,
            'transaction_type': 'sell',
            'price': 1.23,
            'quantity': 5,
            'amount': 6.15,
        }
        d = map_detail_row_to_model(row)
        self.assertEqual(d.transaction_type, 'sell')


if __name__ == '__main__':
    unittest.main(verbosity=2)


