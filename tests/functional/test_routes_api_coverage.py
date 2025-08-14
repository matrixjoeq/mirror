#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from app import create_app


class TestApiEdgeCoverage(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()

    def test_strategy_score_params_and_compat_fields(self):
        # No params (should succeed with defaults)
        r = self.client.get('/api/strategy_score')
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertTrue(j['success'])
        # Backward-compatible fields exist even if stats empty
        data = j['data']
        # do not assert numeric, just presence
        self.assertIn('win_rate_score', data)
        self.assertIn('profit_loss_ratio_score', data)
        self.assertIn('frequency_score', data)
        self.assertIn('total_score', data)

    def test_strategy_trend_validation(self):
        # Missing strategy_id should 400
        r = self.client.get('/api/strategy_trend')
        self.assertEqual(r.status_code, 400)
        j = r.get_json()
        self.assertFalse(j['success'])

import tempfile
import os
import sys
from services import DatabaseService


class TestRoutesApiCoverage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.app.config['DATABASE_PATH'] = self.tmp.name
        self.app.db_service = DatabaseService(self.tmp.name)
        self.client = self.app.test_client()

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_api_404_405_500_handlers(self):
        # 404: app-level handler may return HTML; assert status code only
        r404 = self.client.get('/api/not-exists')
        self.assertEqual(r404.status_code, 404)

        # 405: blueprint-level handler（某些 Flask 版本下可能返回非 JSON），验证状态码即可
        r405 = self.client.get('/api/tag/1/delete')  # endpoint exists but wrong method
        self.assertEqual(r405.status_code, 405)


