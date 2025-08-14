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


if __name__ == '__main__':
    unittest.main(verbosity=2)


