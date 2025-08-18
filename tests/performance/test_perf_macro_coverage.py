#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from app import create_app


class TestPerfMacroCoverage(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()

    def test_macro_endpoints_fast(self):
        r1 = self.client.get('/api/macro/snapshot?window=1y')
        self.assertEqual(r1.status_code, 200)
        r2 = self.client.get('/api/macro/country?economy=US&window=6m')
        self.assertEqual(r2.status_code, 200)
        r3 = self.client.get('/api/macro/score?entity_type=macro&entity_id=US&view=value')
        self.assertEqual(r3.status_code, 200)
        r4 = self.client.post('/api/macro/refresh')
        self.assertEqual(r4.status_code, 200)


if __name__ == '__main__':
    unittest.main()


