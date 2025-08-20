#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from services.meso_service import MesoService


def test_meso_list_indexes_has_minimum_entries():
    svc = MesoService()
    lst = svc.list_indexes()
    assert isinstance(lst, list)
    assert any(i.get('symbol') == '^GSPC' for i in lst)


def test_meso_compare_series_limit_and_shape():
    svc = MesoService()
    data = svc.get_compare_series(['^GSPC', '^NDX'], window='1y', currency='USD')
    assert data['symbols'] == ['^GSPC', '^NDX']
    assert 'series' in data
    assert isinstance(data['series'].get('^GSPC'), list)


