#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from decimal import Decimal

from app import create_app


class TestTradingServiceBranches(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.svc = self.app.trading_service
        self.strategy = self.app.strategy_service
        ok, _ = self.strategy.create_strategy('BRANCH', '')
        if not ok:
            pass

    def tearDown(self):
        self.ctx.pop()

    def test_overview_with_no_sell_has_zero_rates(self):
        ok, tid = self.svc.add_buy_transaction('BRANCH', 'B0', '无卖出', Decimal('1.000'), 100, '2025-01-01', Decimal('0.1'))
        self.assertTrue(ok)
        ov = self.svc.get_trade_overview_metrics(tid)
        # 分母为0时，比例应为0
        self.assertEqual(ov['sell_qty'], 0)
        self.assertEqual(ov['gross_profit_rate'], 0.0)
        self.assertEqual(ov['net_profit_rate'], 0.0)

    def test_fifo_remaining_map_clamped(self):
        ok, tid = self.svc.add_buy_transaction('BRANCH', 'B1', '超卖出', Decimal('1.000'), 100, '2025-01-01', Decimal('0.1'))
        self.assertTrue(ok)
        ok2, msg2 = self.svc.add_sell_transaction(tid, Decimal('1.100'), 50, '2025-01-02', Decimal('0.1'))
        self.assertTrue(ok2, msg2)
        # 直接操作数据库插入异常卖出（超过持仓），仅为覆盖保护逻辑
        self.app.db_service.execute_query(
            "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee) VALUES (?, 'sell', 1.1, 100, 110.0, '2025-01-03', 0.1)",
            (tid,), fetch_all=False
        )
        rem = self.svc.compute_buy_detail_remaining_map(tid)
        # 只有一条买入，剩余应不小于0
        self.assertGreaterEqual(next(iter(rem.values())), 0)


if __name__ == '__main__':
    unittest.main()


