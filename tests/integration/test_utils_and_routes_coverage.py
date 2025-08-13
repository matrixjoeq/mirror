#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest

from app import create_app
from utils import helpers


class TestUtilsAndRoutesCoverage(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()

    def tearDown(self):
        self.ctx.pop()

    def test_utils_helpers(self):
        self.assertTrue(helpers.validate_date_format('2025-01-01'))
        self.assertFalse(helpers.validate_date_format('2025-13-40'))
        self.assertEqual(helpers.format_currency(1234.5), '¥1,234.50')
        self.assertEqual(helpers.format_percentage(12.3456, 2), '12.35%')
        self.assertEqual(helpers.parse_decimal_input('1,234.50'), 1234.5)
        self.assertEqual(helpers.get_period_date_range('2025', 'year')[0], '2025-01-01')

    def test_more_pages(self):
        for path in ['/strategy_scores', '/symbol_comparison', '/time_comparison']:
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200)


if __name__ == '__main__':
    unittest.main()


