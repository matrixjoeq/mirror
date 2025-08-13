#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from services.database_service import DatabaseService


class TestDatabaseServicePrecheck(unittest.TestCase):
    def test_block_semicolon_and_param_without_placeholder(self):
        db = DatabaseService(':memory:')
        # semicolon should be blocked
        with self.assertRaises(ValueError):
            db.execute_query("SELECT 1;", ())
        # providing params without placeholders should be blocked
        with self.assertRaises(ValueError):
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1", (1,))

    def test_block_union_and_or_true(self):
        db = DatabaseService(':memory:')
        # UNION SELECT pattern
        with self.assertRaises(ValueError):
            db.execute_query("SELECT 1 UNION SELECT 1", ())
        # OR 1=1 pattern
        with self.assertRaises(ValueError):
            db.execute_query("SELECT * FROM trades WHERE 1=1 OR 1=1", ())


if __name__ == '__main__':
    unittest.main()


