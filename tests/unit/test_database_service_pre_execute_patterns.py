#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService


class TestDatabaseServicePreExecutePatterns(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_dbsvc_pat_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_pre_execute_block_union_or(self):
        with self.assertRaises(ValueError):
            self.db._pre_execute_check("SELECT x FROM t /*comment*/ UNION SELECT y FROM t2", ())
        with self.assertRaises(ValueError):
            self.db._pre_execute_check("SELECT * FROM t WHERE a='1' -- inline\n OR 1=1", ())


if __name__ == '__main__':
    unittest.main()


