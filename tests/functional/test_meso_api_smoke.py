#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from app import create_app


def test_meso_api_endpoints_smoke():
    app = create_app('testing')
    client = app.test_client()

    r = client.get('/api/meso/indexes')
    assert r.status_code == 200
    data = r.get_json()
    assert data.get('success') is True
    assert isinstance(data.get('data'), list)

    r2 = client.get('/api/meso/trend_series?symbol=%5EGSPC')
    assert r2.status_code == 200
    d2 = r2.get_json()
    assert d2.get('success') is True
    body = d2.get('data')
    assert body.get('symbol') == '^GSPC'
    assert 'scores' in body and 'prices' in body

    r3 = client.get('/api/meso/compare_series?symbols=%5EGSPC,%5ENDX')
    assert r3.status_code == 200
    d3 = r3.get_json()
    assert d3.get('success') is True
    assert d3.get('data', {}).get('symbols') == ['^GSPC', '^NDX']


