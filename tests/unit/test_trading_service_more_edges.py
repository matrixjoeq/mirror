#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
from decimal import Decimal

from services import DatabaseService, TradingService, StrategyService


class TestTradingServiceMoreEdges(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = DatabaseService(self.temp_db.name)
        self.strategy = StrategyService(self.db)
        self.trading = TradingService(self.db)
        ok, _ = self.strategy.create_strategy('边界策略', '')
        self.sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '边界策略')

    def test_invalid_inputs(self):
        ok, msg = self.trading.add_buy_transaction(self.sid, '', 'X', Decimal('1.0'), 1, '2025-01-01')
        self.assertFalse(ok)
        ok, msg = self.trading.add_buy_transaction(self.sid, 'X', '', Decimal('1.0'), 1, '2025-01-01')
        self.assertFalse(ok)
        ok, msg = self.trading.add_buy_transaction(self.sid, 'X', 'Y', Decimal('0'), 1, '2025-01-01')
        self.assertFalse(ok)
        ok, msg = self.trading.add_buy_transaction(self.sid, 'X', 'Y', Decimal('1.0'), 0, '2025-01-01')
        self.assertFalse(ok)

    def test_update_trade_record_recompute(self):
        ok, trade_id = self.trading.add_buy_transaction(self.sid, 'EDG001', '边界股', Decimal('10.00'), 100, '2025-01-01')
        self.assertTrue(ok)
        # 增加一次买入
        ok, _ = self.trading.add_buy_transaction(self.sid, 'EDG001', '边界股', Decimal('12.00'), 100, '2025-01-02')
        self.assertTrue(ok)
        details = self.trading.get_trade_details(trade_id)
        buy_detail = next(d for d in details if d['transaction_type'] == 'buy')

        # 修改第一笔买入价格，触发重算
        ok, msg = self.trading.update_trade_record(trade_id, [
            {'detail_id': buy_detail['id'], 'price': Decimal('11.00')}
        ])
        self.assertTrue(ok, msg)
        trade = self.trading.get_trade_by_id(trade_id)
        self.assertEqual(trade['total_buy_quantity'], 200)
        self.assertEqual(trade['remaining_quantity'], 200)


if __name__ == '__main__':
    unittest.main(verbosity=2)


