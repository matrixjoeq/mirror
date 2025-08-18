#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from services import mappers


class TestMappersMoreEdgeCases(unittest.TestCase):
    def test_normalize_trade_detail_row_types(self):
        row = {
            'remaining_for_quick': '3',
            'can_quick_sell': 1,
            'quantity': '10',
            'price': '12.34',
            'transaction_fee': '0.56',
        }
        n = mappers.normalize_trade_detail_row(row)
        self.assertEqual(n['remaining_for_quick'], 3)
        self.assertTrue(n['can_quick_sell'])
        self.assertEqual(n['quantity'], 10)
        self.assertAlmostEqual(n['price'], 12.34, places=3)
        self.assertAlmostEqual(n['transaction_fee'], 0.56, places=3)

    def test_dict_to_trade_detail_dto_amount_uses_price_times_qty(self):
        # amount in row is ignored for display; should be price*quantity
        row = {
            'id': 1,
            'trade_id': 2,
            'transaction_type': 'sell',
            'price': 10.0,
            'quantity': 7,
            'amount': 1.0,  # should be ignored
            'transaction_date': '2024-01-01',
            'transaction_fee': 0.1,
            'buy_reason': '',
            'sell_reason': '',
            'profit_loss': 0.0,
            'profit_loss_pct': 0.0,
            'created_at': '2024-01-01',
            'is_deleted': 0,
            'delete_date': None,
            'delete_reason': '',
            'operator_note': '',
        }
        dto = mappers.dict_to_trade_detail_dto(row)
        self.assertEqual(dto.amount, 70.0)


if __name__ == '__main__':
    unittest.main()


