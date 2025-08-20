#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import create_app
from services.meso_repository import MesoRepository


def test_meso_api_trend_and_compare_with_seed_data():
    app = create_app('testing')
    with app.app_context():
        repo = MesoRepository()
        repo.upsert_trend_scores([
            {"symbol": "^GSPC", "date": "2024-01-01", "score": 55.0, "components_json": None},
            {"symbol": "^NDX", "date": "2024-01-01", "score": 65.0, "components_json": None},
        ])

    client = app.test_client()
    r1 = client.get('/api/meso/trend_series?symbol=%5EGSPC')
    assert r1.status_code == 200
    d1 = r1.get_json()
    assert d1['success'] is True
    assert d1['data']['symbol'] == '^GSPC'
    assert isinstance(d1['data']['scores'], list)

    r2 = client.get('/api/meso/compare_series?symbols=%5EGSPC,%5ENDX')
    assert r2.status_code == 200
    d2 = r2.get_json()
    assert d2['success'] is True
    assert d2['data']['symbols'] == ['^GSPC', '^NDX']
    assert set(d2['data']['series'].keys()) == {'^GSPC', '^NDX'}


