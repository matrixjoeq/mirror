#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from decimal import Decimal

from app import create_app


class TestTradingServiceDeletePaths(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.svc = self.app.trading_service
        self.strategy = self.app.strategy_service
        ok, _ = self.strategy.create_strategy('DEL', '')
        if not ok:
            pass

    def tearDown(self):
        self.ctx.pop()

    def test_soft_restore_permanent_delete(self):
        # seed one trade
        ok, tid = self.svc.add_buy_transaction('DEL', 'D1', 'DelStock', Decimal('1.0'), 10, '2025-01-01')
        self.assertTrue(ok)
        # partial sell
        ok2, _ = self.svc.add_sell_transaction(tid, Decimal('1.1'), 5, '2025-01-02')
        self.assertTrue(ok2)

        # soft delete
        self.assertTrue(self.svc.soft_delete_trade(tid, 'CODE', 'cleanup', 'note'))
        # restore
        self.assertTrue(self.svc.restore_trade(tid, 'CODE', 'note'))
        # permanently delete (should succeed after restore)
        self.assertTrue(self.svc.permanently_delete_trade(tid, 'CODE', 'CONFIRM', 'cleanup', 'note'))

    def test_edit_trade_paths(self):
        ok, tid = self.svc.add_buy_transaction('DEL', 'E1', 'EditStock', Decimal('2.0'), 20, '2025-02-01')
        self.assertTrue(ok)
        # valid edit
        ok1, msg1 = self.svc.edit_trade(tid, {'symbol_name': 'EditStockX'}, 'rename')
        self.assertTrue(ok1, msg1)
        # soft delete then try edit (should be blocked)
        self.svc.soft_delete_trade(tid, 'X', 'reason')
        ok2, msg2 = self.svc.edit_trade(tid, {'symbol_name': 'EditStockY'}, 'rename again')
        self.assertFalse(ok2)


if __name__ == '__main__':
    unittest.main()


