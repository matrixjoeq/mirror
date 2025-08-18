#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services import mappers


class TestMappersAndDbSecurity(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_mapdb_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_normalize_trade_row_defaults_and_dates(self):
        row = {
            'id': 1,
            'strategy': 'S1',
            'symbol_code': 'AAA',
            'symbol_name': 'Alpha',
            'open_date': '2024-01-01',
            # 缺失 strategy_name，期望由 strategy 回填
            # 缺失 numeric 字段，期望填充为 0
        }
        n = mappers.normalize_trade_row(row)
        self.assertEqual(n['strategy_name'], 'S1')
        for key in mappers.TRADE_NUMERIC_DEFAULTS:
            self.assertIn(key, n)
            self.assertIsInstance(n[key], float)
        self.assertEqual(n['open_date'], '2024-01-01')

        dto = mappers.dict_to_trade_dto(n)
        # 核心字段存在且为数字类型
        self.assertIsInstance(dto.total_buy_amount, float)
        self.assertIsInstance(dto.total_net_profit_pct, float)

    def test_pre_execute_check_blocks_unsafe_queries(self):
        # 直接调用受测方法以覆盖安全分支
        # 1) 分号（多语句）
        with self.assertRaises(ValueError):
            self.db._pre_execute_check("SELECT 1; SELECT 2", ())
        # 2) 提供参数但未使用占位符
        with self.assertRaises(ValueError):
            self.db._pre_execute_check("SELECT 1", ("x",))
        # 3) 典型注入模式 UNION SELECT
        with self.assertRaises(ValueError):
            self.db._pre_execute_check("SELECT a FROM t UNION SELECT b FROM t2", ())
        # 4) 典型注入 OR 1=1
        with self.assertRaises(ValueError):
            self.db._pre_execute_check("SELECT * FROM t WHERE a = 'x' OR 1=1", ())


if __name__ == '__main__':
    unittest.main()


