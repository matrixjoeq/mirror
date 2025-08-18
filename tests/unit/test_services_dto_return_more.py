#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.strategy_service import StrategyService


class TestServicesDtoReturnMore(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_services_dto_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = StrategyService(self.db)

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_create_and_get_all_strategies_dto(self):
        ok, msg = self.svc.create_strategy('S1', 'd')
        self.assertTrue(ok, msg)
        items = self.svc.get_all_strategies(return_dto=True)
        self.assertTrue(items)
        self.assertTrue(hasattr(items[0], 'name'))


if __name__ == '__main__':
    unittest.main()


