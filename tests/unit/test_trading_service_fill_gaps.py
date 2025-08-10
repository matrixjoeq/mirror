#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
from decimal import Decimal

from services import DatabaseService, TradingService, StrategyService


class TestTradingServiceFillGaps(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)
        self.strategy = StrategyService(self.db)
        self.trading = TradingService(self.db)
        ok, _ = self.strategy.create_strategy('交易补齐', '')
        self.sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '交易补齐')

    def test_add_sell_edge_paths(self):
        ok, trade_id = self.trading.add_buy_transaction(self.sid, 'EDGE', '边界', Decimal('10'), 10, '2025-01-01')
        self.assertTrue(ok)
        # 卖出数量超过剩余
        ok2, msg2 = self.trading.add_sell_transaction(trade_id, Decimal('11'), 100, '2025-01-02')
        self.assertFalse(ok2)
        self.assertIn('超过剩余', msg2)

        # 先全部卖出，第二次卖出应提示已平仓
        ok3, msg3 = self.trading.add_sell_transaction(trade_id, Decimal('11'), 10, '2025-01-02')
        self.assertTrue(ok3)
        ok4, msg4 = self.trading.add_sell_transaction(trade_id, Decimal('12'), 1, '2025-01-03')
        self.assertFalse(ok4)
        self.assertIn('已平仓', msg4)

    def test_get_deleted_and_restore_permanent_delete(self):
        ok, trade_id = self.trading.add_buy_transaction(self.sid, 'DEL', '删', Decimal('10'), 1, '2025-01-01')
        self.assertTrue(ok)
        # 软删除
        self.assertTrue(self.trading.soft_delete_trade(trade_id, 'CODE', '测试删除'))
        deleted = self.trading.get_deleted_trades()
        self.assertTrue(any(t['id'] == trade_id for t in deleted))
        # 恢复
        self.assertTrue(self.trading.restore_trade(trade_id, 'CODE'))
        deleted_after = self.trading.get_deleted_trades()
        self.assertFalse(any(t['id'] == trade_id for t in deleted_after))
        # 永久删除
        self.assertTrue(self.trading.permanently_delete_trade(trade_id, 'CODE', 'CONFIRM', '测试删除'))
        self.assertIsNone(self.trading.get_trade_by_id(trade_id))


if __name__ == '__main__':
    unittest.main(verbosity=2)


