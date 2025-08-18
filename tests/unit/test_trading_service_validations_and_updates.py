#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestTradingServiceValidationsAndUpdates(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_valid_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = TradingService(self.db)
        # 策略
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("策略一",)},
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_add_buy_transaction_validation_errors(self):
        # 缺少标的信息
        ok, msg = self.svc.add_buy_transaction(1, "", "", 10, 1, "2024-01-01")
        self.assertFalse(ok)
        self.assertIn("不能为空", msg)

        # 非法价格/数量
        ok2, msg2 = self.svc.add_buy_transaction(1, "AAA", "Alpha", 0, 0, "2024-01-01")
        self.assertFalse(ok2)
        self.assertIn("必须大于0", msg2)

        # 非法日期
        ok3, msg3 = self.svc.add_buy_transaction(1, "AAA", "Alpha", 10, 100, "2024/01/01")
        self.assertFalse(ok3)
        self.assertIn("日期格式", msg3)

        # 不存在的策略
        ok4, msg4 = self.svc.add_buy_transaction(9999, "AAA", "Alpha", 10, 100, "2024-01-01")
        self.assertFalse(ok4)
        self.assertIn("策略ID", msg4)

    def test_add_buy_then_sell_and_remaining_map(self):
        # 有效买入
        ok, res = self.svc.add_buy_transaction(1, "AAA", "Alpha", 10, 100, "2024-01-01", 1)
        self.assertTrue(ok)
        trade_id = res

        # 第二笔买入
        ok2, _ = self.svc.add_buy_transaction(1, "AAA", "Alpha", 20, 100, "2024-01-02", 1)
        self.assertTrue(ok2)

        # 计算可卖剩余（按 FIFO）
        remap = self.svc.compute_buy_detail_remaining_map(trade_id)
        self.assertEqual(sum(remap.values()), 200)

        # 非法卖出（数量<=0）
        ok3, msg3 = self.svc.add_sell_transaction(trade_id, 25, 0, "2024-01-03", 1, "test")
        self.assertFalse(ok3)
        self.assertIn("必须大于0", msg3)

    def test_update_trade_record_errors(self):
        # 先插入一笔交易与明细
        ok, res = self.svc.add_buy_transaction(1, "AAA", "Alpha", 10, 100, "2024-01-01", 1)
        self.assertTrue(ok)
        trade_id = res

        # 缺少 detail_id
        ok2, msg2 = self.svc.update_trade_record(trade_id, [{'price': 11}])
        self.assertFalse(ok2)
        self.assertIn("detail_id", msg2)

        # 不存在的 detail_id
        ok3, msg3 = self.svc.update_trade_record(trade_id, [{'detail_id': 999999, 'price': 11}])
        self.assertFalse(ok3)
        self.assertIn("不存在于交易", msg3)


if __name__ == '__main__':
    unittest.main()


