#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService


class TestDatabaseServiceSecurityAndTx(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_dbsvc_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_execute_transaction_rollback_on_error(self):
        # second operation will fail due to missing param, expect False and nothing committed from that op
        ops = [
            { 'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S",) },
            { 'query': "INSERT INTO strategies (name) VALUES (?)", 'params': () },  # incorrect bindings
        ]
        ok = self.db.execute_transaction(ops)
        self.assertFalse(ok)

    def test_pre_execute_check_rejects_semicolons(self):
        with self.assertRaises(ValueError):
            self.db._pre_execute_check("SELECT 1;", ())


if __name__ == '__main__':
    unittest.main()


