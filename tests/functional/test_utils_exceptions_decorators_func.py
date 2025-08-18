#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from utils.decorators import handle_errors, require_json, require_confirmation_code
from utils.exceptions import ValidationError, NotFoundError, ConflictError, UnauthorizedError, ForbiddenError
from app import create_app


class TestUtilsExceptionsDecoratorsFunctional(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()

    def _wrap(self, exc):
        @handle_errors
        def endpoint():
            raise exc
        return endpoint

    def test_handle_errors_mapping(self):
        with self.app.test_request_context('/'):
            # Flask 视图函数可返回 (Response, status)
            self.assertEqual(self._wrap(ValidationError('x'))()[1], 400)
            self.assertEqual(self._wrap(NotFoundError('x'))()[1], 404)
            self.assertEqual(self._wrap(ConflictError('x'))()[1], 409)
            self.assertEqual(self._wrap(UnauthorizedError('x'))()[1], 401)
            self.assertEqual(self._wrap(ForbiddenError('x'))()[1], 403)

    def test_require_json_decorator(self):
        @require_json
        def ok_json():
            return 'ok', 200

        with self.app.test_request_context('/', method='POST', data='a=b', content_type='application/x-www-form-urlencoded'):
            resp = ok_json()
            self.assertEqual(resp[1], 400)

        with self.app.test_request_context('/', method='POST', data='{}', content_type='application/json'):
            resp2 = ok_json()
            self.assertEqual(resp2[1], 200)

    def test_require_confirmation_code_decorator(self):
        @require_confirmation_code
        def ok_code():
            return 'ok', 200

        with self.app.test_request_context('/', method='POST', data={}):
            resp = ok_code()
            self.assertEqual(resp[1], 400)

        with self.app.test_request_context('/', method='POST', data='{"confirmation_code":"X"}', content_type='application/json'):
            resp2 = ok_code()
            self.assertEqual(resp2[1], 200)


if __name__ == '__main__':
    unittest.main()


