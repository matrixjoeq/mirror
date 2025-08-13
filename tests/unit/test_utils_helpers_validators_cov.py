#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from utils import helpers, validators


class TestUtilsHelpersValidatorsCoverage(unittest.TestCase):
    def test_helpers_basic(self):
        code = helpers.generate_confirmation_code(4)
        self.assertEqual(len(code), 4)

        y1 = helpers.get_period_date_range('2025', 'year')
        self.assertEqual(y1, ('2025-01-01', '2025-12-31'))

        q1 = helpers.get_period_date_range('2025-Q2', 'quarter')
        self.assertEqual(q1, ('2025-04-01', '2025-06-30'))

        m1 = helpers.get_period_date_range('2025-02', 'month')
        self.assertEqual(m1, ('2025-02-01', '2025-02-28'))

        anyp = helpers.get_period_date_range('na', 'any')
        self.assertEqual(anyp, ('1900-01-01', '2099-12-31'))

        self.assertEqual(helpers.format_currency(1234.5, '¥'), '¥1,234.50')
        self.assertEqual(helpers.format_percentage(12.3456, 2), '12.35%')

        self.assertEqual(helpers.parse_decimal_input('1,234.50'), 1234.5)
        self.assertEqual(helpers.parse_decimal_input(None), 0.0)

        self.assertTrue(helpers.validate_date_format('2025-01-01'))
        self.assertFalse(helpers.validate_date_format('2025-13-01'))

        self.assertGreaterEqual(helpers.get_trading_days_between('2025-01-01', '2025-01-10'), 0)

    def test_validators_basic(self):
        ok, msg = validators.validate_positive_decimal('1.23')
        self.assertTrue(ok)
        ok, msg = validators.validate_positive_decimal('-1')
        self.assertFalse(ok)
        ok, msg = validators.validate_positive_decimal('abc')
        self.assertFalse(ok)

        ok, msg = validators.validate_positive_int('2')
        self.assertTrue(ok)
        ok, msg = validators.validate_positive_int('0')
        self.assertFalse(ok)
        ok, msg = validators.validate_positive_int(None)
        self.assertFalse(ok)

        ok, msg = validators.validate_date_yyyy_mm_dd('2025-01-01')
        self.assertTrue(ok)
        ok, msg = validators.validate_date_yyyy_mm_dd('2025-13-01')
        self.assertFalse(ok)
        ok, msg = validators.validate_date_yyyy_mm_dd('2025-02-30')
        self.assertFalse(ok)


if __name__ == '__main__':
    unittest.main()


