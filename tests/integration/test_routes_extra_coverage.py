#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from app import create_app


class TestRoutesExtraCoverage(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()

    def tearDown(self):
        self.ctx.pop()

    def test_admin_and_analysis_pages(self):
        # admin diagnose page
        r1 = self.client.get('/admin/db/diagnose')
        self.assertEqual(r1.status_code, 200)
        # strategy scores and comparison
        r2 = self.client.get('/strategy_scores')
        self.assertEqual(r2.status_code, 200)
        r3 = self.client.get('/symbol_comparison')
        self.assertEqual(r3.status_code, 200)
        r4 = self.client.get('/time_comparison')
        self.assertEqual(r4.status_code, 200)


if __name__ == '__main__':
    unittest.main()


