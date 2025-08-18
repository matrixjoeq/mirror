#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestTradingServiceGetTradesPaginatedEdges(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_pages_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = TradingService(self.db)
        # Strategy and a couple of trades
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
        ])
        ok1, t1 = self.svc.add_buy_transaction(1, "AAA", "Alpha", 10, 100, "2024-01-01", 1)
        self.assertTrue(ok1)
        ok2, t2 = self.svc.add_buy_transaction(1, "BBB", "Beta", 12, 50, "2024-01-02", 0.5)
        self.assertTrue(ok2)

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_symbols_and_names_filters_both(self):
        items, total = self.svc.get_trades_paginated(
            status=None,
            strategy=None,
            order_by='t.open_date ASC',
            page=1,
            page_size=25,
            return_dto=True,
            symbols=["AAA", "CCC"],
            symbol_names=["Alpha"],
        )
        self.assertEqual(total, 1)
        self.assertEqual(items[0].symbol_code, 'AAA')

    def test_invalid_page_and_dir_and_sort_key(self):
        # invalid page/page_size get normalized internally via route, but service still handles provided values
        items, total = self.svc.get_trades_paginated(
            status=None, strategy=None, order_by='invalid', page=-1, page_size=0, return_dto=True
        )
        self.assertTrue(total >= 2)


if __name__ == '__main__':
    unittest.main()


