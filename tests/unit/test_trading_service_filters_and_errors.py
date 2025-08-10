#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
from decimal import Decimal

from services import DatabaseService, TradingService, StrategyService


class TestTradingServiceFiltersAndErrors(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)
        self.strategy = StrategyService(self.db)
        self.trading = TradingService(self.db)
        ok, _ = self.strategy.create_strategy('过滤策略', '')
        self.sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '过滤策略')

        # 开仓
        ok, self.trade_id = self.trading.add_buy_transaction(self.sid, 'FIL001', '过滤股', Decimal('10.00'), 100, '2025-01-01')
        self.assertTrue(ok)

    def test_sell_more_than_remaining_and_sell_after_closed(self):
        # 超量卖出 -> 失败
        ok, msg = self.trading.add_sell_transaction(self.trade_id, Decimal('11.00'), 200, '2025-01-02')
        self.assertFalse(ok)
        self.assertIn('超过剩余持仓', msg)

        # 正常卖出全部 -> closed
        ok, msg = self.trading.add_sell_transaction(self.trade_id, Decimal('11.00'), 100, '2025-01-03')
        self.assertTrue(ok, msg)

        # 已平仓后再次卖出 -> 失败
        ok, msg = self.trading.add_sell_transaction(self.trade_id, Decimal('12.00'), 1, '2025-01-04')
        self.assertFalse(ok)
        self.assertIn('已平仓', msg)

    def test_filters_by_status_and_strategy(self):
        # 新增另一笔保持 open
        ok, trade2 = self.trading.add_buy_transaction(self.sid, 'FIL002', '过滤股2', Decimal('10.00'), 50, '2025-01-05')
        self.assertTrue(ok)

        # open 过滤
        open_trades = self.trading.get_all_trades(status='open')
        self.assertTrue(any(t['symbol_code'] == 'FIL002' for t in open_trades))

        # 按策略（id）过滤
        by_id = self.trading.get_all_trades(strategy=self.sid)
        self.assertGreaterEqual(len(by_id), 2)

        # 按策略（name）过滤
        by_name = self.trading.get_all_trades(strategy='过滤策略')
        self.assertEqual(len(by_id), len(by_name))

    def test_invalid_strategy_type(self):
        # 提供不支持的策略类型 -> 失败
        ok, msg = self.trading.add_buy_transaction({'id': self.sid}, 'BAD', '坏', Decimal('1.0'), 1, '2025-01-01')
        self.assertFalse(ok)


if __name__ == '__main__':
    unittest.main(verbosity=2)


