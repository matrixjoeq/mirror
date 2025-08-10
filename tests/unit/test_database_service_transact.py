#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile

from services import DatabaseService


class TestDatabaseServiceTransact(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)

    def test_execute_transaction_success_and_failure(self):
        # 成功事务：创建标签
        ops = [
            {"query": "INSERT INTO strategy_tags (name, created_at) VALUES (?, CURRENT_TIMESTAMP)", "params": ("单测标签",)},
        ]
        ok = self.db.execute_transaction(ops)
        self.assertTrue(ok)

        # 失败事务：错误SQL应返回False
        bad_ops = [
            {"query": "INSERT INTO strategy_tags (name) VALUES (?)", "params": ()},  # 缺少参数
        ]
        ok = self.db.execute_transaction(bad_ops)
        self.assertFalse(ok)


if __name__ == '__main__':
    unittest.main(verbosity=2)


