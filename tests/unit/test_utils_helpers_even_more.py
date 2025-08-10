#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from utils.helpers import get_period_date_range, get_trading_days_between


class TestUtilsHelpersEvenMore(unittest.TestCase):
    def test_get_period_date_range_year_and_default(self):
        # year branch
        self.assertEqual(get_period_date_range('2024', 'year'), ('2024-01-01', '2024-12-31'))
        # unknown period type -> default full range
        self.assertEqual(get_period_date_range('anything', 'unknown'), ('1900-01-01', '2099-12-31'))

    def test_get_trading_days_between_invalid_dates(self):
        # invalid format should return 0
        self.assertEqual(get_trading_days_between('invalid-date', '2024-01-01'), 0)
        self.assertEqual(get_trading_days_between('2024-01-01', 'bad'), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)


