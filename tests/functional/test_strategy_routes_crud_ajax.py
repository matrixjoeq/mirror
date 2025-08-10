#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import tempfile
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app
from services import DatabaseService, StrategyService


class TestStrategyRoutesCrudAjax(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.tmp.close()
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['DATABASE_PATH'] = self.tmp.name
        self.db = DatabaseService(self.tmp.name)
        self.app.db_service = self.db
        self.strategy = StrategyService(self.db)
        self.client = self.app.test_client()

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_create_edit_delete_strategy_ajax(self):
        # GET page OK
        self.assertEqual(self.client.get('/strategy/create').status_code, 200)

        # AJAX create invalid (empty name)
        r_invalid = self.client.post(
            '/strategy/create',
            data={'name': '', 'description': '', 'tag_names': []},
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(r_invalid.status_code, 200)
        j1 = r_invalid.get_json()
        self.assertIsNotNone(j1)
        self.assertFalse(j1.get('success'))

        # AJAX create valid
        r_valid = self.client.post(
            '/strategy/create',
            data={'name': 'A1', 'description': 'd', 'tag_names': ['趋势', '自定义']},
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(r_valid.status_code, 200)
        j2 = r_valid.get_json()
        self.assertTrue(j2.get('success'))

        # Prepare another strategy for name conflict
        self.strategy.create_strategy('A2', '')
        sid_a2 = next(s['id'] for s in self.strategy.get_all_strategies() if s['name'] == 'A2')

        # AJAX edit with name conflict
        r_conflict = self.client.post(
            f'/strategy/{sid_a2}/edit',
            data={'name': 'A1', 'description': 'x', 'tags': []},
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(r_conflict.status_code, 200)
        j3 = r_conflict.get_json()
        self.assertFalse(j3.get('success'))

        # AJAX edit success
        r_ok = self.client.post(
            f'/strategy/{sid_a2}/edit',
            data={'name': 'A2-new', 'description': 'x', 'tags': []},
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        self.assertEqual(r_ok.status_code, 200)
        j4 = r_ok.get_json()
        self.assertTrue(j4.get('success'))

        # Delete strategy with no trades
        r_del = self.client.post(f'/strategy/{sid_a2}/delete')
        self.assertEqual(r_del.status_code, 200)
        self.assertTrue(r_del.get_json().get('success'))


if __name__ == '__main__':
    unittest.main(verbosity=2)


