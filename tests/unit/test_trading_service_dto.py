#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
import os
from services import DatabaseService, TradingService, StrategyService
from services.mappers import TradeDTO, dict_to_trade_dto


class TestTradingServiceDTO(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.db = DatabaseService(self.tmp.name)
        self.trading = TradingService(self.db)
        self.strategy = StrategyService(self.db)
        self.strategy.create_strategy('DTO策略', 'dto')
        self.sid = self.strategy.get_all_strategies()[0]['id']

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_get_all_trades_as_dto(self):
        ok, tid = self.trading.add_buy_transaction(
            strategy=self.sid,
            symbol_code='D001',
            symbol_name='DTO1',
            price=1.0,
            quantity=10,
            transaction_date='2025-01-01'
        )
        self.assertTrue(ok)
        items = self.trading.get_all_trades(return_dto=True)
        # 现阶段直接返回 DTO
        self.assertIsInstance(items[0], TradeDTO)
        self.assertEqual(items[0].symbol_code, 'D001')


if __name__ == '__main__':
    unittest.main(verbosity=2)


