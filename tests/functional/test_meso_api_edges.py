#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import create_app


def test_meso_compare_series_symbols_param_validation():
    app = create_app('testing')
    client = app.test_client()

    # empty
    r = client.get('/api/meso/compare_series?symbols=')
    assert r.status_code == 400
    body = r.get_json()
    assert body.get('success') is False

    # >10
    too_many = ','.join([f'S{i}' for i in range(11)])
    r2 = client.get(f'/api/meso/compare_series?symbols={too_many}')
    assert r2.status_code == 400
    body2 = r2.get_json()
    assert body2.get('success') is False


