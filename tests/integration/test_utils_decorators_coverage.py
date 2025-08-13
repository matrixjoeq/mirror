#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from flask import Flask, jsonify

from utils.decorators import require_confirmation_code, handle_errors, require_json


class TestUtilsDecoratorsCoverage(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)

        @app.route('/need_code', methods=['POST'])
        @require_confirmation_code
        def need_code():
            return jsonify({'ok': True})

        @app.route('/boom')
        @handle_errors
        def boom():
            raise ValueError('x')

        @app.route('/need_json', methods=['POST'])
        @require_json
        def need_json():
            return jsonify({'ok': True})

        self.client = app.test_client()

    def test_require_confirmation_code_and_json(self):
        # missing confirmation_code
        r1 = self.client.post('/need_code', data={})
        self.assertEqual(r1.status_code, 400)
        # has confirmation_code
        r2 = self.client.post('/need_code', data={'confirmation_code': 'X'})
        self.assertIn(r2.status_code, [200, 302])
        # require_json
        r3 = self.client.post('/need_json', data={})
        self.assertEqual(r3.status_code, 400)
        r4 = self.client.post('/need_json', json={})
        self.assertEqual(r4.status_code, 200)

    def test_handle_errors(self):
        r = self.client.get('/boom')
        self.assertEqual(r.status_code, 500)


if __name__ == '__main__':
    unittest.main()


