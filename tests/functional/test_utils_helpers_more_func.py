#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from utils import helpers


class TestUtilsHelpersMoreFunctional(unittest.TestCase):
    def test_format_helpers_and_parsers(self):
        self.assertEqual(helpers.format_currency(1234.5, '¥'), '¥1,234.50')
        self.assertEqual(helpers.format_percentage(12.3456, 2), '12.35%')
        self.assertEqual(helpers.parse_decimal_input('1,234.56'), 1234.56)
        self.assertEqual(helpers.parse_decimal_input('abc'), 0.0)

    def test_date_helpers(self):
        self.assertTrue(helpers.validate_date_format('2024-01-31'))
        self.assertFalse(helpers.validate_date_format('2024/01/31'))
        s, e = helpers.get_period_date_range('2024', 'year')
        self.assertEqual((s, e), ('2024-01-01', '2024-12-31'))


if __name__ == '__main__':
    unittest.main()


