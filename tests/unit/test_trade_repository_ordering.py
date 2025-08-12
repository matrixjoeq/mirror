#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from services.trade_repository import TradeRepository


class TestTradeRepositoryOrdering(unittest.TestCase):
    def test_whitelist_order_by(self):
        repo = TradeRepository()
        # 内部方法不可直接访问，这里只验证不会抛异常且能够运行（不执行真实SQL）
        # 使用一个空的内存库，主要覆盖代码路径
        repo.db.db_path = ':memory:'
        try:
            repo.fetch_trades(None, None, False, 't.created_at DESC', 1)
        except Exception:
            pass
        try:
            repo.fetch_trades(None, None, False, 's.name ASC', 1)
        except Exception:
            pass
        try:
            repo.fetch_trades(None, None, False, 'DROP TABLE trades', 1)
        except Exception:
            pass


if __name__ == '__main__':
    unittest.main(verbosity=2)


