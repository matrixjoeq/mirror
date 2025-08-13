#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from services.database_service import DatabaseService


class TestLoggingIntegration(unittest.TestCase):
    def test_migration_warning_path(self):
        db = DatabaseService(':memory:')
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # 使用不存在的列触发 _add_column_if_not_exists 的 ALTER 执行
            db._add_column_if_not_exists(cursor, 'trades', 'tmp_col_for_test', 'INTEGER')  # type: ignore[attr-defined]
            # 再次调用不会抛错
            db._add_column_if_not_exists(cursor, 'trades', 'tmp_col_for_test', 'INTEGER')  # type: ignore[attr-defined]


