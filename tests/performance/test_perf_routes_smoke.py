#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from app import create_app


class TestPerfRoutesSmoke(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()

    def tearDown(self):
        self.ctx.pop()

    def test_core_pages(self):
        for path in ['/', '/trades', '/deleted_trades', '/strategy_scores', '/symbol_comparison', '/time_comparison', '/admin/db/diagnose']:
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200)


if __name__ == '__main__':
    unittest.main()


