#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from utils.validators import (
    validate_positive_decimal,
    validate_positive_int,
    validate_date_yyyy_mm_dd,
)


class TestValidators(unittest.TestCase):
    def test_positive_decimal(self):
        ok, _ = validate_positive_decimal('1.23')
        self.assertTrue(ok)
        ok2, msg = validate_positive_decimal('-1')
        self.assertFalse(ok2)
        self.assertIn('价格', msg)

    def test_positive_int(self):
        ok, _ = validate_positive_int('10')
        self.assertTrue(ok)
        ok2, msg = validate_positive_int('0')
        self.assertFalse(ok2)
        self.assertIn('数量', msg)

    def test_date(self):
        ok, _ = validate_date_yyyy_mm_dd('2025-01-01')
        self.assertTrue(ok)
        ok2, msg = validate_date_yyyy_mm_dd('2025/01/01')
        self.assertFalse(ok2)
        self.assertIn('日期', msg)


if __name__ == '__main__':
    unittest.main(verbosity=2)


