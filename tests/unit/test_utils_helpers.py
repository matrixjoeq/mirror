#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from utils import helpers


class TestUtilsHelpers(unittest.TestCase):
    def test_format_currency_and_percentage(self):
        self.assertEqual(helpers.format_currency(1234.5, '¥'), '¥1,234.50')
        self.assertEqual(helpers.format_percentage(12.3456, 2), '12.35%')

    def test_parse_decimal_input(self):
        self.assertEqual(helpers.parse_decimal_input('1,234.56'), 1234.56)
        self.assertEqual(helpers.parse_decimal_input('invalid'), 0.0)
        self.assertEqual(helpers.parse_decimal_input(None), 0.0)

    def test_validate_date_and_trading_days(self):
        self.assertTrue(helpers.validate_date_format('2024-01-31'))
        self.assertFalse(helpers.validate_date_format('2024-02-30'))
        days = helpers.get_trading_days_between('2024-01-01', '2024-01-31')
        self.assertGreaterEqual(days, 20)


if __name__ == '__main__':
    unittest.main(verbosity=2)


