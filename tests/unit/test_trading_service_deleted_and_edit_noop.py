#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestTradingServiceDeletedAndEditNoop(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_del_", suffix=".db")
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

    def test_add_sell_when_trade_deleted(self):
        # 新建买入
        ok, res = self.svc.add_buy_transaction(1, "AAA", "Alpha", 10, 100, "2024-01-01", 1)
        self.assertTrue(ok)
        trade_id = int(res)
        # 标记删除
        self.db.execute_query("UPDATE trades SET is_deleted = 1 WHERE id = ?", (trade_id,), fetch_all=False)
        # 卖出应失败并提示
        ok2, msg2 = self.svc.add_sell_transaction(trade_id, 20, 10, "2024-01-02", 0.5, "r")
        self.assertFalse(ok2)
        self.assertIn("已被删除", msg2)

    def test_edit_trade_no_updates(self):
        ok, res = self.svc.add_buy_transaction(1, "BBB", "Beta", 10, 100, "2024-01-01", 1)
        self.assertTrue(ok)
        trade_id = int(res)
        ok2, msg2 = self.svc.edit_trade(trade_id, {}, 'noop')
        self.assertFalse(ok2)
        self.assertIn("没有提供有效更新字段", msg2)

    def test_resolve_strategy(self):
        # 通过名称解析
        sid = self.svc._resolve_strategy("策略一")
        self.assertEqual(sid, 1)
        # 不存在的名称返回 None
        self.assertIsNone(self.svc._resolve_strategy("不存在"))


if __name__ == '__main__':
    unittest.main()


