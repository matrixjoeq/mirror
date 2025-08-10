#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app
from services import DatabaseService


class TestStrategyRoutesNonAjax(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['DATABASE_PATH'] = self.tmp.name
        self.db = DatabaseService(self.tmp.name)
        self.app.db_service = self.db
        self.client = self.app.test_client()

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_create_strategy_non_ajax_invalid_then_valid(self):
        # invalid -> stays on page with error
        r1 = self.client.post('/strategy/create', data={'name': '', 'description': ''})
        self.assertEqual(r1.status_code, 200)

        # valid -> redirect to list
        r2 = self.client.post('/strategy/create', data={'name': 'NA1', 'description': 'd'})
        self.assertIn(r2.status_code, (302, 303))


if __name__ == '__main__':
    unittest.main(verbosity=2)


