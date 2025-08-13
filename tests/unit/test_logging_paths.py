#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import sqlite3
from unittest.mock import MagicMock

from services.trading_service import TradingService
from services.database_service import DatabaseService


class _DummyDb:
    def get_connection(self):
        raise RuntimeError("forced failure")


class TestLoggingPaths(unittest.TestCase):
    def test_trading_service_exception_paths(self):
        svc = TradingService()
        # force get_connection to fail to hit logging branches
        svc.db = _DummyDb()  # type: ignore

        self.assertFalse(svc.soft_delete_trade(1, confirmation_code='X', delete_reason='r'))
        self.assertFalse(svc.restore_trade(1, confirmation_code='X'))
        self.assertFalse(svc.permanently_delete_trade(1, confirmation_code='X', confirmation_text='DELETE', delete_reason='r'))
        self.assertFalse(svc.record_modification(1, None, 'edit', 'field', 'old', 'new', 'why'))

    def test_database_service_migration_warning_path(self):
        db = DatabaseService(':memory:')
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # monkeypatch _add_column_if_not_exists to raise OperationalError once
            calls = {'n': 0}

            def boom(*args, **kwargs):
                calls['n'] += 1
                raise sqlite3.OperationalError('boom')

            original = db._add_column_if_not_exists  # type: ignore[attr-defined]
            try:
                db._add_column_if_not_exists = boom  # type: ignore[assignment]
                # Should not raise; warning path is logged
                db._handle_database_migrations(cursor)  # type: ignore[arg-type]
            finally:
                db._add_column_if_not_exists = original  # type: ignore[assignment]


