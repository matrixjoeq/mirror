#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from decimal import Decimal

from services.trade_calculation import compute_trade_profit_metrics


class TestTradeCalculation(unittest.TestCase):
    def test_compute_metrics_basic(self):
        m = compute_trade_profit_metrics(
            gross_buy_total=Decimal('1000'),  # 100*10
            buy_fees_total=Decimal('5.00'),
            gross_sell_total=Decimal('1150'), # 100*11.5
            sell_fees_total=Decimal('2.00'),
            sold_qty=Decimal('100'),
            buy_qty=Decimal('100'),
        )
        self.assertAlmostEqual(m['avg_buy_price_ex_fee'], 10.0, places=3)
        self.assertAlmostEqual(m['buy_cost_for_sold'], 1000.0, places=3)
        self.assertAlmostEqual(m['gross_profit_for_sold'], 150.0, places=3)
        # net = 150 - 2 - 分摊买入费(5)
        self.assertAlmostEqual(m['net_profit'], 143.0, places=3)
        self.assertGreater(m['net_profit_pct'], 0.0)
        self.assertAlmostEqual(m['total_buy_amount_incl_fee'], 1005.0, places=3)
        self.assertAlmostEqual(m['total_sell_amount_net'], 1148.0, places=3)
        self.assertAlmostEqual(m['total_fees'], 7.0, places=3)

    def test_zero_buy_qty(self):
        m = compute_trade_profit_metrics(
            gross_buy_total=Decimal('0'),
            buy_fees_total=Decimal('0'),
            gross_sell_total=Decimal('0'),
            sell_fees_total=Decimal('0'),
            sold_qty=Decimal('0'),
            buy_qty=Decimal('0'),
        )
        # 所有派生字段应为0，不抛异常
        for k, v in m.items():
            self.assertEqual(v, 0.0)

    def test_fee_ratio_when_gross_buy_zero(self):
        m = compute_trade_profit_metrics(
            gross_buy_total=Decimal('0'),
            buy_fees_total=Decimal('10'),
            gross_sell_total=Decimal('100'),
            sell_fees_total=Decimal('1'),
            sold_qty=Decimal('10'),
            buy_qty=Decimal('10'),
        )
        # 分母为0时费用占比为0
        self.assertEqual(m['total_fee_ratio_pct'], 0.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)


