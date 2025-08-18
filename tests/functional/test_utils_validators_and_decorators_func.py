#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from utils import validators


class TestUtilsValidatorsFunctional(unittest.TestCase):
    def test_validators_messages(self):
        ok_p, msg_p = validators.validate_positive_decimal("-1")
        self.assertFalse(ok_p)
        self.assertIn("价格", msg_p)

        ok_q, msg_q = validators.validate_positive_int("abc")
        self.assertFalse(ok_q)
        self.assertIn("数量", msg_q)

        ok_d, msg_d = validators.validate_date_yyyy_mm_dd("2024/01/01")
        self.assertFalse(ok_d)
        self.assertIn("日期", msg_d)


if __name__ == '__main__':
    unittest.main()


