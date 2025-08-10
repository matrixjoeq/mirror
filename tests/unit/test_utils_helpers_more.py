#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from utils.helpers import get_period_date_range


class TestUtilsHelpersMore(unittest.TestCase):
    def test_get_period_date_range_quarter(self):
        self.assertEqual(get_period_date_range('2024-Q1', 'quarter'), ('2024-01-01', '2024-03-31'))
        self.assertEqual(get_period_date_range('2024-Q2', 'quarter'), ('2024-04-01', '2024-06-30'))
        self.assertEqual(get_period_date_range('2024-Q3', 'quarter'), ('2024-07-01', '2024-09-30'))
        self.assertEqual(get_period_date_range('2024-Q4', 'quarter'), ('2024-10-01', '2024-12-31'))

    def test_get_period_date_range_month(self):
        self.assertEqual(get_period_date_range('2024-01', 'month'), ('2024-01-01', '2024-01-31'))
        self.assertEqual(get_period_date_range('2024-02', 'month'), ('2024-02-01', '2024-02-28'))
        self.assertEqual(get_period_date_range('2024-04', 'month'), ('2024-04-01', '2024-04-30'))


if __name__ == '__main__':
    unittest.main(verbosity=2)


