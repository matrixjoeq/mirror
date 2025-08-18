#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestTradingServiceOverviewAndPagination(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = TradingService(self.db)

        # 策略
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("策略一",)},
        ])

        # 一笔交易，含两笔买入与一笔卖出，以覆盖 WAC 与费用分摊
        ops = [
            {
                'query': (
                    "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, status, is_deleted) "
                    "VALUES (?, ?, ?, ?, ?, ?, 0)"
                ),
                'params': (1, "策略一", "AAA", "Alpha", "2024-01-01", "open"),
            },
            # buy #1: 10 * 100, fee 1
            {
                'query': (
                    "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) "
                    "VALUES (?, 'buy', ?, ?, ?, ?, ?, 0)"
                ),
                'params': (1, 10.0, 100, 10.0 * 100, "2024-01-01", 1.0),
            },
            # buy #2: 20 * 100, fee 1
            {
                'query': (
                    "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) "
                    "VALUES (?, 'buy', ?, ?, ?, ?, ?, 0)"
                ),
                'params': (1, 20.0, 100, 20.0 * 100, "2024-01-02", 1.0),
            },
            # sell: 25 * 150, fee 3
            {
                'query': (
                    "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) "
                    "VALUES (?, 'sell', ?, ?, ?, ?, ?, 0)"
                ),
                'params': (1, 25.0, 150, 25.0 * 150, "2024-01-03", 3.0),
            },
        ]
        self.db.execute_transaction(ops)

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_get_trade_overview_metrics(self):
        metrics = self.svc.get_trade_overview_metrics(1)
        # 基础成交额
        self.assertEqual(round(metrics['total_buy_amount'], 3), 3000.000)
        self.assertEqual(round(metrics['total_sell_amount'], 3), 3750.000)
        # 费用与占比
        self.assertEqual(round(metrics['total_buy_fees'], 3), 2.000)
        self.assertEqual(round(metrics['total_sell_fees'], 3), 3.000)
        self.assertEqual(round(metrics['total_fees'], 3), 5.000)
        self.assertEqual(round(metrics['total_fee_ratio_pct'], 3), round(5.0 / 3000.0 * 100, 3))
        # 盈亏（基于卖出份额的加权平均成本）
        # WAC(ex fee) = 3000/200 = 15; gross = (25-15)*150=1500; net = 1500-3-(2*0.75)=1495.5
        self.assertEqual(round(metrics['total_profit_loss'], 3), 1500.000)
        self.assertEqual(round(metrics['total_net_profit'], 3), 1495.500)
        self.assertEqual(round(metrics['total_net_profit_pct'], 3), round((1495.5 / (15 * 150)) * 100, 3))

    def test_get_trades_paginated_returns_dto_with_metrics(self):
        items, total = self.svc.get_trades_paginated(status=None, strategy=None, order_by='t.open_date ASC',
                                                     page=1, page_size=25, return_dto=True)
        self.assertEqual(total, 1)
        self.assertEqual(len(items), 1)
        dto = items[0]
        # DTO 内包含关键指标字段
        for key in [
            'total_buy_amount', 'total_sell_amount', 'total_gross_profit', 'total_net_profit',
            'total_net_profit_pct', 'total_buy_fees', 'total_sell_fees', 'total_fees', 'total_fee_ratio_pct'
        ]:
            self.assertIn(key, dto.__dict__)


if __name__ == '__main__':
    unittest.main()


