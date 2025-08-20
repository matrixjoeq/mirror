#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from services.meso_service import MesoService


class TestMesoServiceEdges(unittest.TestCase):
    def test_meso_compare_series_symbols_limit_validation(self):
        svc = MesoService()
        with self.assertRaises(ValueError):
            svc.get_compare_series([], window='3y', currency='USD')
        with self.assertRaises(ValueError):
            svc.get_compare_series(['S' + str(i) for i in range(11)], window='3y', currency='USD')


    def test_meso_trend_series_shape_keys_present(self):
        svc = MesoService()
        resp = svc.get_trend_series('^GSPC', window='1y', currency='USD')
        self.assertTrue(set(resp.keys()) >= {"symbol", "window", "currency", "scores", "prices"})


if __name__ == '__main__':
    unittest.main()


