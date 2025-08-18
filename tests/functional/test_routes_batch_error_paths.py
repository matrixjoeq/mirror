#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from app import create_app


class TestRoutesBatchErrorPaths(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()

    def test_batch_delete_missing_params(self):
        # 缺少 trade_ids
        resp = self.client.post('/batch_delete_trades', data={})
        self.assertEqual(resp.status_code, 400)

        # 缺少确认码
        resp2 = self.client.post('/batch_delete_trades', data={'trade_ids[]': ['1', '2']})
        self.assertEqual(resp2.status_code, 400)

    def test_batch_restore_missing_params(self):
        resp = self.client.post('/batch_restore_trades', data={})
        self.assertEqual(resp.status_code, 400)

        resp2 = self.client.post('/batch_restore_trades', data={'trade_ids[]': ['1']})
        self.assertEqual(resp2.status_code, 400)

    def test_batch_permanently_delete_missing_params(self):
        resp = self.client.post('/batch_permanently_delete_trades', data={})
        self.assertEqual(resp.status_code, 400)

        resp2 = self.client.post('/batch_permanently_delete_trades', data={'trade_ids[]': ['1']})
        self.assertEqual(resp2.status_code, 400)

        resp3 = self.client.post('/batch_permanently_delete_trades', data={'trade_ids[]': ['1'], 'confirmation_code': '123'})
        self.assertEqual(resp3.status_code, 400)


if __name__ == '__main__':
    unittest.main()


