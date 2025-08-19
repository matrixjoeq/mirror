#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from app import create_app


class TestMacroRoutesAndApi(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()

    def test_macro_pages(self):
        r1 = self.client.get('/macro')
        self.assertEqual(r1.status_code, 200)
        r2 = self.client.get('/macro/country?economy=US')
        self.assertEqual(r2.status_code, 200)
        r3 = self.client.get('/macro/compare')
        self.assertEqual(r3.status_code, 200)

    def test_macro_api(self):
        r1 = self.client.get('/api/macro/snapshot?window=1y&view=trend')
        self.assertEqual(r1.status_code, 200)
        j1 = r1.get_json()
        self.assertIn('economies', j1)
        self.assertIn('ranking', j1)
        self.assertEqual(j1.get('window'), '1y')
        self.assertEqual(j1.get('view'), 'trend')

        r2 = self.client.get('/api/macro/country?economy=DE')
        self.assertEqual(r2.status_code, 200)
        j2 = r2.get_json()
        self.assertEqual(j2['economy'], 'DE')

        r3 = self.client.get('/api/macro/score?entity_type=commodity&entity_id=gold&view=trend')
        self.assertEqual(r3.status_code, 200)
        j3 = r3.get_json()
        self.assertEqual(j3['entity_type'], 'commodity')
        self.assertEqual(j3['entity_id'], 'gold')

        # refresh endpoint (POST)
        r4 = self.client.post('/api/macro/refresh')
        self.assertEqual(r4.status_code, 200)
        j4 = r4.get_json()
        self.assertTrue(j4.get('refreshed'))

        # status endpoint
        r5 = self.client.get('/api/macro/status')
        self.assertEqual(r5.status_code, 200)
        j5 = r5.get_json()
        self.assertIn('history', j5)


if __name__ == '__main__':
    unittest.main()


