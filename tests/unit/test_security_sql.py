#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from services.database_service import DatabaseService


class TestSQLSecurity(unittest.TestCase):
    def setUp(self):
        # 使用内存数据库即可验证拦截逻辑
        self.db = DatabaseService(':memory:')

    def test_block_multiple_statements(self):
        with self.assertRaises(ValueError):
            self.db.execute_query("SELECT 1; SELECT 2")

    def test_require_placeholders_when_params(self):
        with self.assertRaises(ValueError):
            self.db.execute_query("SELECT 1", params=("x",))

    def test_block_suspicious_union(self):
        with self.assertRaises(ValueError):
            self.db.execute_query("SELECT * FROM users UNION SELECT password FROM users")

    def test_allow_comments_in_ddl(self):
        # 应允许带注释的DDL
        self.db.execute_query("""
            /* create table */
            CREATE TABLE t (id INTEGER);
        """.strip(' \n;'))


if __name__ == '__main__':
    unittest.main(verbosity=2)


