#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from datetime import datetime

from services import mappers


class TestMappersMapModels(unittest.TestCase):
    def test_map_trade_row_to_model_and_dates(self):
        row = {
            'id': 1,
            'strategy_id': 2,
            'strategy': 'S',
            'symbol_code': 'AAA',
            'symbol_name': 'Alpha',
            'open_date': '2024-01-01',
            'close_date': datetime(2024, 1, 10),
            'status': 'open',
            'total_buy_amount': 0,
            'total_buy_quantity': 0,
            'total_sell_amount': 0,
            'total_sell_quantity': 0,
            'remaining_quantity': 0,
            'total_profit_loss': 0,
            'total_profit_loss_pct': 0,
            'holding_days': 0,
            'trade_log': '',
            'created_at': '2024-01-01',
            'updated_at': '2024-01-02',
            'is_deleted': 0,
            'delete_date': None,
            'delete_reason': '',
            'operator_note': '',
        }
        model = mappers.map_trade_row_to_model(row)
        self.assertEqual(model.id, 1)
        self.assertEqual(model.symbol_code, 'AAA')
        self.assertIsNotNone(model.created_at)
        self.assertIsNotNone(model.updated_at)

    def test_map_detail_row_to_model(self):
        row = {
            'id': 5,
            'trade_id': 1,
            'transaction_type': 'buy',
            'price': 10,
            'quantity': 2,
            'amount': 20,
            'transaction_date': '2024-01-01',
            'transaction_fee': 1,
            'buy_reason': '',
            'sell_reason': '',
            'profit_loss': 0,
            'profit_loss_pct': 0,
            'created_at': '2024-01-01',
            'is_deleted': 0,
            'delete_date': None,
            'delete_reason': '',
            'operator_note': '',
        }
        model = mappers.map_detail_row_to_model(row)
        self.assertEqual(model.id, 5)
        self.assertEqual(model.trade_id, 1)


if __name__ == '__main__':
    unittest.main()


