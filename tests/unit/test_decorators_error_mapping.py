#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from flask import Flask, jsonify

from utils.decorators import handle_errors
from utils.exceptions import (
    ValidationError,
    NotFoundError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    DomainError,
)


def make_app():
    app = Flask(__name__)

    @app.route('/ok')
    @handle_errors
    def ok():
        return jsonify({'success': True})

    @app.route('/validation')
    @handle_errors
    def validation():
        raise ValidationError('bad input')

    @app.route('/notfound')
    @handle_errors
    def notfound():
        raise NotFoundError('missing')

    @app.route('/conflict')
    @handle_errors
    def conflict():
        raise ConflictError('dup')

    @app.route('/unauth')
    @handle_errors
    def unauth():
        raise UnauthorizedError('noauth')

    @app.route('/forbid')
    @handle_errors
    def forbid():
        raise ForbiddenError('nope')

    @app.route('/domain')
    @handle_errors
    def domain():
        raise DomainError('biz')

    @app.route('/boom')
    @handle_errors
    def boom():
        raise RuntimeError('boom')

    return app


class TestErrorMapping(unittest.TestCase):
    def setUp(self):
        self.app = make_app()
        self.client = self.app.test_client()

    def test_ok(self):
        resp = self.client.get('/ok')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['success'])

    def test_validation(self):
        resp = self.client.get('/validation')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()['code'], 'validation_error')

    def test_notfound(self):
        resp = self.client.get('/notfound')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json()['code'], 'not_found')

    def test_conflict(self):
        resp = self.client.get('/conflict')
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.get_json()['code'], 'conflict')

    def test_unauthorized(self):
        resp = self.client.get('/unauth')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()['code'], 'unauthorized')

    def test_forbidden(self):
        resp = self.client.get('/forbid')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()['code'], 'forbidden')

    def test_domain(self):
        resp = self.client.get('/domain')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()['code'], 'domain_error')

    def test_generic(self):
        resp = self.client.get('/boom')
        self.assertEqual(resp.status_code, 500)
        j = resp.get_json()
        self.assertEqual(j['code'], 'internal_error')
        self.assertFalse(j['success'])


if __name__ == '__main__':
    unittest.main(verbosity=2)


