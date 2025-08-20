#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from services.meso_service import MesoService


def test_compare_series_boundary_10_symbols():
    svc = MesoService()
    symbols = [f'SYM{i}' for i in range(10)]
    out = svc.get_compare_series(symbols, window='6m', currency='USD')
    assert out['symbols'] == symbols
    assert set(out.keys()) >= {'symbols', 'window', 'currency', 'series'}


