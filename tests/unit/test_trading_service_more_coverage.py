#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
import os
from decimal import Decimal

from services import DatabaseService, TradingService, StrategyService


class TestTradingServiceMoreCoverage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)
        self.trading = TradingService(self.db)
        self.strategy = StrategyService(self.db)

        ok, _ = self.strategy.create_strategy('覆盖策略', '用于覆盖率补充')
        strategies = self.strategy.get_all_strategies()
        self.sid = next(s['id'] for s in strategies if s['name'] == '覆盖策略')

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def _create_trade_with_details(self):
        ok, tid = self.trading.add_buy_transaction(
            strategy=self.sid,
            symbol_code='COV001',
            symbol_name='覆盖标的',
            price=Decimal('10.00'),
            quantity=100,
            transaction_date='2025-01-01',
            transaction_fee=Decimal('1.00'),
        )
        self.assertTrue(ok)
        # 第二笔买入
        ok2, tid2 = self.trading.add_buy_transaction(
            strategy=self.sid,
            symbol_code='COV001',
            symbol_name='覆盖标的',
            price=Decimal('12.00'),
            quantity=50,
            transaction_date='2025-01-02',
            transaction_fee=Decimal('0.50'),
        )
        self.assertTrue(ok2)
        self.assertEqual(tid, tid2)
        return tid

    def test_overview_and_fifo_remaining_and_soft_restore_delete(self):
        tid = self._create_trade_with_details()

        # 部分卖出，便于概览计算
        ok, msg = self.trading.add_sell_transaction(
            trade_id=tid,
            price=Decimal('11.00'),
            quantity=80,
            transaction_date='2025-01-03',
            transaction_fee=Decimal('0.80'),
            sell_reason='部分卖出',
        )
        self.assertTrue(ok, msg)

        # 覆盖 get_trade_overview_metrics
        ov = self.trading.get_trade_overview_metrics(tid)
        self.assertIn('gross_profit', ov)
        self.assertIn('net_profit', ov)
        self.assertGreaterEqual(ov['sell_qty'], 80)

        # 覆盖 FIFO 剩余计算
        remaining_map = self.trading.compute_buy_detail_remaining_map(tid)
        self.assertTrue(all(isinstance(v, int) for v in remaining_map.values()))
        self.assertGreater(sum(remaining_map.values()), 0)

        # 覆盖软删除与恢复
        self.assertTrue(self.trading.soft_delete_trade(tid, confirmation_code='XXXX', delete_reason='测试删除'))
        deleted = [t for t in self.trading.get_deleted_trades() if t['id'] == tid]
        self.assertEqual(len(deleted), 1)

        self.assertTrue(self.trading.restore_trade(tid, confirmation_code='XXXX'))
        active = [t for t in self.trading.get_all_trades() if t['id'] == tid]
        self.assertEqual(len(active), 1)

        # 覆盖永久删除
        self.assertTrue(self.trading.permanently_delete_trade(tid, confirmation_code='XXXX', confirmation_text='DELETE', delete_reason='清理', operator_note='note'))
        none_left = [t for t in self.trading.get_all_trades(include_deleted=True) if t['id'] == tid]
        self.assertEqual(len(none_left), 0)

    def test_update_trade_record_success_path(self):
        tid = self._create_trade_with_details()
        # 先卖出一部分，生成卖出明细，便于更新
        ok, msg = self.trading.add_sell_transaction(
            trade_id=tid,
            price=Decimal('11.50'),
            quantity=50,
            transaction_date='2025-01-04',
            transaction_fee=Decimal('0.50'),
            sell_reason='校准',
        )
        self.assertTrue(ok, msg)

        # 读取明细，选择一条卖出明细进行更新
        details = self.trading.get_trade_details(tid)
        sell_detail = next(d for d in details if d['transaction_type'] == 'sell')

        ok2, msg2 = self.trading.update_trade_record(
            tid,
            [{
                'detail_id': sell_detail['id'],
                'price': Decimal('12.00'),
                'transaction_fee': Decimal('0.30'),
                'sell_reason': '调整价格'
            }]
        )
        self.assertTrue(ok2, msg2)


if __name__ == '__main__':
    unittest.main(verbosity=2)


