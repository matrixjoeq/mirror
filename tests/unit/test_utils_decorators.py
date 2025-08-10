#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from flask import Flask, jsonify
from utils.decorators import require_json, handle_errors, require_confirmation_code


class TestUtilsDecorators(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)

        @app.route('/json_only', methods=['POST'])
        @require_json
        def json_only():
            return jsonify({'success': True})

        @app.route('/error_route')
        @handle_errors
        def error_route():
            raise RuntimeError('boom')

        @app.route('/need_code', methods=['POST'])
        @require_confirmation_code
        def need_code():
            return jsonify({'success': True})

        self.client = app.test_client()

    def test_require_json(self):
        resp = self.client.post('/json_only', data='not json', headers={'Content-Type': 'text/plain'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('JSON', resp.get_data(as_text=True))

        resp = self.client.post('/json_only', json={'a': 1})
        self.assertEqual(resp.status_code, 200)

    def test_handle_errors(self):
        resp = self.client.get('/error_route')
        self.assertEqual(resp.status_code, 500)
        data = resp.get_json()
        self.assertIsNotNone(data)
        self.assertFalse(data.get('success'))
        self.assertIn('boom', data.get('message', ''))

    def test_require_confirmation_code(self):
        resp = self.client.post('/need_code', json={'x': 1})
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post('/need_code', json={'confirmation_code': 'ABC123'})
        self.assertEqual(resp.status_code, 200)


if __name__ == '__main__':
    unittest.main(verbosity=2)


