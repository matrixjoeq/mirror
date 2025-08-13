#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import sqlite3

from services.database_service import DatabaseService
from services.trading_service import TradingService


class TestServicesLoggingFunctional(unittest.TestCase):
    def test_execute_transaction_error_path(self):
        db = DatabaseService(':memory:')
        # 使用分号触发预执行检查异常，从而走到 execute_transaction 的异常分支
        ok = db.execute_transaction([
            {'query': 'SELECT 1; SELECT 2', 'params': ()},
        ])
        self.assertFalse(ok)

    def test_trading_service_warning_paths(self):
        # 构造一个将抛出异常的伪 DB 以触发 warning 分支
        class _DummyDb:
            def get_connection(self):
                raise RuntimeError('boom')

        svc = TradingService()
        svc.db = _DummyDb()  # type: ignore
        self.assertFalse(svc.soft_delete_trade(1, confirmation_code='X', delete_reason='t'))
        self.assertFalse(svc.restore_trade(1, confirmation_code='X'))


