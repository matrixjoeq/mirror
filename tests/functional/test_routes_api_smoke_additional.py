#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from app import create_app


class TestApiSmokeAdditional(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()

    def test_home_index_200(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)

    def test_symbol_lookup_and_trade_detail_smoke(self):
        r1 = self.client.get('/api/symbol_lookup?symbol_code=AAA')
        self.assertEqual(r1.status_code, 200)
        # trade_detail 采用路径参数，未知ID返回404
        r2 = self.client.get('/api/trade_detail/1')
        # 在空环境可能为404，容忍 200/404
        self.assertIn(r2.status_code, (200, 404))

    def test_api_error_paths_coverage(self):
        # trade_detail 404
        r404 = self.client.get('/api/trade_detail/999999')
        self.assertEqual(r404.status_code, 404)
        # modify_trade_detail 缺少 detail_id
        r400 = self.client.post('/api/modify_trade_detail', data={})
        self.assertEqual(r400.status_code, 400)

    def test_batch_endpoints_error_paths(self):
        # Ensure error JSON paths are covered
        self.assertEqual(self.client.post('/batch_delete_trades', data={}).status_code, 400)
        self.assertEqual(self.client.post('/batch_restore_trades', data={}).status_code, 400)
        self.assertEqual(self.client.post('/batch_permanently_delete_trades', data={}).status_code, 400)


if __name__ == '__main__':
    unittest.main(verbosity=2)


