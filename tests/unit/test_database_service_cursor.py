#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile

from services import DatabaseService


class TestDatabaseServiceCursor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)

    def test_executemany_and_executescript_block(self):
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.executemany(
                "INSERT INTO strategy_tags (name, created_at) VALUES (?, CURRENT_TIMESTAMP)",
                [("批1",), ("批2",)]
            )
            res = conn.cursor().execute("SELECT COUNT(*) AS c FROM strategy_tags")
            self.assertGreaterEqual(res.fetchone()['c'], 2)

            with self.assertRaises(RuntimeError):
                cur.executescript("CREATE TABLE x(a INTEGER);")


if __name__ == '__main__':
    unittest.main(verbosity=2)


