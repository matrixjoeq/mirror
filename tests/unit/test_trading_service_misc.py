#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from decimal import Decimal

from app import create_app


class TestTradingServiceMisc(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.svc = self.app.trading_service

    def tearDown(self):
        self.ctx.pop()

    def test_get_deleted_trades_empty(self):
        deleted = self.svc.get_deleted_trades()
        self.assertIsInstance(deleted, list)


