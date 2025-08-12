#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from services.mappers import map_trade_row_to_model, map_detail_row_to_model


class TestMappersMore(unittest.TestCase):
    def test_trade_defaults_and_dates(self):
        # 缺失字段与异常日期格式应安全回退
        row = {
            'id': 2,
            'symbol_code': 'XYZ',
            'open_date': '2025-01-01',
            'created_at': '2025-01-01 10:00:00',
            'updated_at': 'bad-date',
            'is_deleted': None,
        }
        t = map_trade_row_to_model(row)
        self.assertEqual(t.id, 2)
        self.assertEqual(t.symbol_code, 'XYZ')
        self.assertEqual(t.status, 'open')
        self.assertIsNone(t.updated_at)

    def test_detail_defaults(self):
        row = {
            'trade_id': 3,
            'quantity': 0,
        }
        d = map_detail_row_to_model(row)
        self.assertEqual(d.trade_id, 3)
        self.assertEqual(d.transaction_type, 'buy')


if __name__ == '__main__':
    unittest.main(verbosity=2)


