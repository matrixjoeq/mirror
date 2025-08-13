#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from decimal import Decimal

from services.trade_calculation import compute_trade_profit_metrics


class TestTradeCalculationMore(unittest.TestCase):
    def test_edge_zero_denominator(self):
        m = compute_trade_profit_metrics(
            Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0')
        )
        self.assertEqual(m['net_profit_pct'], 0.0)
        self.assertEqual(m['total_fee_ratio_pct'], 0.0)


if __name__ == '__main__':
    unittest.main()


