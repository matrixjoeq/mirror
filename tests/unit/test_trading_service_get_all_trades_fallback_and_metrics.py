#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest
from decimal import Decimal

from services.database_service import DatabaseService
from services.trading_service import TradingService
from services.trade_repository import TradeRepository


class _RepoStub(TradeRepository):
    def aggregate_trade_details(self, trade_id: int, include_deleted: bool):  # type: ignore[override]
        raise RuntimeError("boom")


class TestTradingServiceGetAllTradesFallbackAndMetrics(unittest.TestCase):
    def setUp(self):
        fd, self.tmp_db = tempfile.mkstemp(prefix="mirror_unit_trading_all_fallback_", suffix=".db")
        os.close(fd)
        self.db = DatabaseService(self.tmp_db)
        self.svc = TradingService(self.db)
        # One strategy and one trade with details to compute metrics
        self.db.execute_transaction([
            {'query': "INSERT INTO strategies (name) VALUES (?)", 'params': ("S1",)},
            {'query': "INSERT INTO trades (strategy_id, strategy, symbol_code, symbol_name, open_date, close_date, status, is_deleted, holding_days) VALUES (1,'S1','AAA','Alpha','2024-01-01','2024-01-10','closed',0,9)", 'params': ()},
        ])
        self.db.execute_transaction([
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (1,'buy',10,100,1000,'2024-01-01',1,0)", 'params': ()},
            {'query': "INSERT INTO trade_details (trade_id, transaction_type, price, quantity, amount, transaction_date, transaction_fee, is_deleted) VALUES (1,'sell',12,100,1199,'2024-01-10',1,0)", 'params': ()},
        ])

    def tearDown(self):
        try:
            os.remove(self.tmp_db)
        except Exception:
            pass

    def test_get_all_trades_metrics_normal(self):
        rows = self.svc.get_all_trades(status='closed', return_dto=False)
        self.assertTrue(rows)
        # 验证关键字段存在
        for key in ['total_buy_amount','total_sell_amount','total_fees','total_profit_loss']:
            self.assertIn(key, rows[0])

    def test_get_all_trades_fallback_on_repo_error(self):
        # Inject stub repo to trigger fallback branch
        self.svc.trade_repo = _RepoStub(self.db)  # type: ignore[assignment]
        rows = self.svc.get_all_trades(status='closed', return_dto=False)
        self.assertTrue(rows)
        self.assertIn('total_fees', rows[0])


if __name__ == '__main__':
    unittest.main()


