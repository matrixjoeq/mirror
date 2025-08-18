#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
from datetime import date, timedelta

import unittest

from services.database_service import DatabaseService
from services.trade_repository import TradeRepository


class TestTradeRepositoryFilters(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_repo_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.repo = TradeRepository(self.db)

        # 插入基础数据（仅 trades，不强制 strategy_id）
        d0 = date.today()
        d1 = d0 - timedelta(days=10)
        d2 = d0 - timedelta(days=5)
        ops = [
            {
                'query': (
                    "INSERT INTO trades (strategy, symbol_code, symbol_name, open_date, close_date, status, is_deleted) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)"
                ),
                'params': ("trend", "AAA", "Alpha", d1.isoformat(), d0.isoformat(), "closed", 0),
            },
            {
                'query': (
                    "INSERT INTO trades (strategy, symbol_code, symbol_name, open_date, close_date, status, is_deleted) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)"
                ),
                'params': ("trend", "BBB", "Beta", d2.isoformat(), None, "open", 0),
            },
            {
                'query': (
                    "INSERT INTO trades (strategy, symbol_code, symbol_name, open_date, close_date, status, is_deleted) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)"
                ),
                'params': ("trend", "CCC", "Gamma", d1.isoformat(), None, "open", 1),
            },
        ]
        self.db.execute_transaction(ops)

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_fetch_excludes_deleted_by_default(self):
        rows = self.repo.fetch_trades(status=None, strategy_id=None, include_deleted=False,
                                      order_by='t.open_date DESC', limit=None)
        # 仅返回未删除的两条
        self.assertEqual(len(rows), 2)
        codes = {r['symbol_code'] for r in rows}
        self.assertEqual(codes, {"AAA", "BBB"})

    def test_symbols_and_names_filters(self):
        # 按代码过滤（大小写不敏感）
        rows = self.repo.fetch_trades(status=None, strategy_id=None, include_deleted=False,
                                      order_by='t.open_date DESC', limit=None,
                                      symbols=["aaa", "ccc"])  # ccc 被删除
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['symbol_code'], "AAA")

        # 按名称过滤（大小写不敏感）
        rows2 = self.repo.fetch_trades(status=None, strategy_id=None, include_deleted=False,
                                       order_by='t.open_date DESC', limit=None,
                                       symbol_names=["beta"])  # 命中 BBB
        self.assertEqual(len(rows2), 1)
        self.assertEqual(rows2[0]['symbol_name'], "Beta")

    def test_date_range_filters(self):
        # 只给 date_from
        rows_from = self.repo.fetch_trades(status=None, strategy_id=None, include_deleted=False,
                                           order_by='t.open_date DESC', limit=None,
                                           date_from=(date.today() - timedelta(days=7)).isoformat())
        # 按实现口径：开仓或平仓日期>=from 均视为命中，因此 AAA(平仓在范围内) 与 BBB(开仓在范围内) 都命中
        self.assertEqual(len(rows_from), 2)

        # 只给 date_to
        rows_to = self.repo.fetch_trades(status=None, strategy_id=None, include_deleted=False,
                                         order_by='t.open_date DESC', limit=None,
                                         date_to=(date.today() - timedelta(days=7)).isoformat())
        self.assertEqual(len(rows_to), 1)  # 仅 AAA

        # 给 from/to 区间
        rows_between = self.repo.fetch_trades(status=None, strategy_id=None, include_deleted=False,
                                              order_by='t.open_date DESC', limit=None,
                                              date_from=(date.today() - timedelta(days=15)).isoformat(),
                                              date_to=(date.today() - timedelta(days=1)).isoformat())
        self.assertEqual(len(rows_between), 2)
        # 覆盖 fetch_trades 无效 order_by 回退路径
        rows_fallback = self.repo.fetch_trades(status=None, strategy_id=None, include_deleted=False,
                                               order_by='invalid', limit=10)
        self.assertTrue(len(rows_fallback) >= 1)

    def test_order_by_whitelist_and_pagination(self):
        # 非白名单排序应回退
        rows = self.repo.fetch_trades(status=None, strategy_id=None, include_deleted=False,
                                      order_by='id DESC; DROP', limit=10, offset=0)
        self.assertEqual(len(rows), 2)

        # 合法排序 + LIMIT 1
        rows2 = self.repo.fetch_trades(status=None, strategy_id=None, include_deleted=False,
                                       order_by='t.open_date ASC', limit=1, offset=0)
        self.assertEqual(len(rows2), 1)

    def test_count_matches_filters(self):
        cnt_all = self.repo.count_trades(status=None, strategy_id=None, include_deleted=False)
        self.assertEqual(cnt_all, 2)

        cnt_open = self.repo.count_trades(status="open", strategy_id=None, include_deleted=False)
        self.assertEqual(cnt_open, 1)

        cnt_symbol = self.repo.count_trades(status=None, strategy_id=None, include_deleted=False,
                                            symbols=["AAA"])  # 命中 AAA
        self.assertEqual(cnt_symbol, 1)


if __name__ == '__main__':
    unittest.main()


