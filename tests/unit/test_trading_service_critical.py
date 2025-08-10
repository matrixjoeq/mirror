#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
from decimal import Decimal

from services import DatabaseService, TradingService, StrategyService


class TestTradingServiceCriticalFlows(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        self.db = DatabaseService(self.temp_db.name)
        self.strategy_service = StrategyService(self.db)
        self.trading = TradingService(self.db)

        ok, _ = self.strategy_service.create_strategy('测试策略', '用于关键路径测试')
        self.assertTrue(ok or '已存在' in _)
        self.strategy_id = next(s['id'] for s in self.strategy_service.get_all_strategies() if s['name'] == '测试策略')

    def tearDown(self):
        pass

    def test_partial_then_full_sell_flow_with_fees_and_holding_days(self):
        ok, trade_id = self.trading.add_buy_transaction(
            strategy=self.strategy_id,
            symbol_code='CRIT001',
            symbol_name='关键路径一号',
            price=Decimal('10.00'),
            quantity=Decimal('300'),
            transaction_date='2025-01-01',
            transaction_fee=Decimal('3.00'),
        )
        self.assertTrue(ok)

        # 第二次买入合并
        ok, _ = self.trading.add_buy_transaction(
            strategy=self.strategy_id,
            symbol_code='CRIT001',
            symbol_name='关键路径一号',
            price=Decimal('12.00'),
            quantity=Decimal('200'),
            transaction_date='2025-01-05',
            transaction_fee=Decimal('2.00'),
        )
        self.assertTrue(ok)

        trade = self.trading.get_trade_by_id(trade_id)
        self.assertEqual(trade['total_buy_quantity'], 500)
        self.assertEqual(trade['remaining_quantity'], 500)

        # 部分卖出 200
        ok, msg = self.trading.add_sell_transaction(
            trade_id=trade_id,
            price=Decimal('13.00'),
            quantity=200,
            transaction_date='2025-01-10',
            transaction_fee=Decimal('2.00'),
            sell_reason='部分止盈'
        )
        self.assertTrue(ok, msg)

        trade = self.trading.get_trade_by_id(trade_id)
        self.assertEqual(trade['status'], 'open')
        self.assertEqual(trade['remaining_quantity'], 300)

        # 全部卖出剩余 300，验证持仓天数基于第一次开仓
        ok, msg = self.trading.add_sell_transaction(
            trade_id=trade_id,
            price=Decimal('11.50'),
            quantity=300,
            transaction_date='2025-02-01',
            transaction_fee=Decimal('3.00'),
            sell_reason='清仓'
        )
        self.assertTrue(ok, msg)

        trade = self.trading.get_trade_by_id(trade_id)
        self.assertEqual(trade['status'], 'closed')
        self.assertEqual(trade['remaining_quantity'], 0)
        # 2025-02-01 - 2025-01-01 = 31 天
        self.assertEqual(trade['holding_days'], 31)

    def test_resolve_strategy_by_id_and_name_and_inactive(self):
        # by id
        ok, trade_id = self.trading.add_buy_transaction(
            strategy=self.strategy_id,
            symbol_code='CRIT002',
            symbol_name='关键解析',
            price=Decimal('9.00'),
            quantity=100,
            transaction_date='2025-01-01'
        )
        self.assertTrue(ok)

        # by name
        ok, trade_id2 = self.trading.add_buy_transaction(
            strategy='测试策略',
            symbol_code='CRIT003',
            symbol_name='关键解析2',
            price=Decimal('9.00'),
            quantity=100,
            transaction_date='2025-01-02'
        )
        self.assertTrue(ok)

        # disable strategy and expect failure
        self.strategy_service.disable_strategy_by_name('测试策略')
        ok, msg = self.trading.add_buy_transaction(
            strategy='测试策略',
            symbol_code='CRIT004',
            symbol_name='关键解析3',
            price=Decimal('9.00'),
            quantity=100,
            transaction_date='2025-01-03'
        )
        self.assertFalse(ok)
        self.assertIn('不存在或已被禁用', msg)


if __name__ == '__main__':
    unittest.main(verbosity=2)


