#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
from decimal import Decimal

from services import DatabaseService, TradingService, StrategyService


class TestTradingServiceAdminPaths(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)
        self.strategy = StrategyService(self.db)
        self.trading = TradingService(self.db)
        ok, _ = self.strategy.create_strategy('管理路径策略', '')
        self.sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '管理路径策略')

    def test_soft_delete_restore_permanent_and_modifications(self):
        ok, trade_id = self.trading.add_buy_transaction(
            strategy=self.sid,
            symbol_code='ADM001',
            symbol_name='管理股',
            price=Decimal('10.00'),
            quantity=100,
            transaction_date='2025-01-01'
        )
        self.assertTrue(ok)

        # 记录一次修改
        recorded = self.trading.record_modification(trade_id, None, 'trade', 'note', 'old', 'new', '测试')
        self.assertTrue(recorded)
        mods = self.trading.get_trade_modifications(trade_id)
        self.assertGreaterEqual(len(mods), 1)

        # 软删除
        ok = self.trading.soft_delete_trade(trade_id, 'CONF1', '清理', '单元测试')
        self.assertTrue(ok)
        deleted = self.trading.get_deleted_trades()
        self.assertTrue(any(t['id'] == trade_id for t in deleted))

        # 恢复
        ok = self.trading.restore_trade(trade_id, 'CONF2', '恢复')
        self.assertTrue(ok)
        active = self.trading.get_all_trades()
        self.assertTrue(any(t['id'] == trade_id for t in active))

        # 永久删除
        ok = self.trading.permanently_delete_trade(trade_id, 'CONF3', 'YES', '清理', '最终')
        self.assertTrue(ok)
        active = self.trading.get_all_trades()
        self.assertFalse(any(t['id'] == trade_id for t in active))


if __name__ == '__main__':
    unittest.main(verbosity=2)


