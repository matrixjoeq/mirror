#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app
from services import DatabaseService, TradingService, StrategyService


class TestSortStatsFunctional(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['DATABASE_PATH'] = self.tmp.name
        self.db = DatabaseService(self.tmp.name)
        self.trading = TradingService(self.db)
        self.strategy = StrategyService(self.db)
        self.app.db_service = self.db
        self.client = self.app.test_client()

        ok, _ = self.strategy.create_strategy('统计排序策略', '')
        self.sid = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == '统计排序策略')

        # 准备两只标的，产生不同统计
        ok, t1 = self.trading.add_buy_transaction(self.sid, 'ST1', '甲', Decimal('10'), 2, '2025-01-01')
        self.trading.add_sell_transaction(t1, Decimal('12'), 2, '2025-01-03')
        ok, t2 = self.trading.add_buy_transaction(self.sid, 'ST2', '乙', Decimal('10'), 3, '2025-01-02')
        self.trading.add_sell_transaction(t2, Decimal('9'), 3, '2025-01-05')

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_sort_by_stats_keys(self):
        for sort_by in ['total_return_rate', 'win_rate', 'total_return', 'avg_return_per_trade']:
            r = self.client.get(f'/strategy_detail/{self.sid}?sort_by={sort_by}&sort_order=desc')
            self.assertEqual(r.status_code, 200)

    def test_trades_filter_by_strategy_name(self):
        # 使用字符串策略名进行过滤
        r = self.client.get('/trades?status=all&strategy=统计排序策略')
        self.assertEqual(r.status_code, 200)


if __name__ == '__main__':
    unittest.main(verbosity=2)


