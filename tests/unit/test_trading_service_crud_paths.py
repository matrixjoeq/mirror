#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestTradingServiceCrudPaths(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_crud_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = TradingService(self.db)
        # 策略
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("策略一",)},
        ])

        # 初始买入
        ok, res = self.svc.add_buy_transaction(1, "AAA", "Alpha", 10, 100, "2024-01-01", 1)
        assert ok
        self.trade_id = int(res)

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_edit_trade_and_modifications(self):
        ok, msg = self.svc.edit_trade(self.trade_id, {'symbol_name': 'AlphaX'}, '调整名称')
        self.assertTrue(ok)
        mods = self.svc.get_trade_modifications(self.trade_id)
        self.assertTrue(isinstance(mods, list))

    def test_update_trade_record_success_and_soft_restore_delete(self):
        # 查询任意一个明细ID
        rows = self.svc.get_trade_details(self.trade_id)
        self.assertTrue(rows)
        detail_id = int(rows[0]['id'])

        # 成功更新明细（不改变类型分支）
        ok, msg = self.svc.update_trade_record(self.trade_id, [{'detail_id': detail_id, 'price': 11, 'transaction_fee': 2}])
        self.assertTrue(ok, msg)

        # 软删除
        self.assertTrue(self.svc.soft_delete_trade(self.trade_id, 'code123', '测试删除'))
        # 恢复
        self.assertTrue(self.svc.restore_trade(self.trade_id, 'code123', '恢复'))
        # 永久删除
        self.assertTrue(self.svc.permanently_delete_trade(self.trade_id, 'code123', 'CONFIRM', '原因', '备注'))


if __name__ == '__main__':
    unittest.main()


