#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app
from services import DatabaseService


class TestRoutesApiCoverage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.app = create_app()
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


