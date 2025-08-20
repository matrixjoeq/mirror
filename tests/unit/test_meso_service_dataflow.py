#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import create_app
from services.meso_service import MesoService
from services.meso_repository import MesoRepository


def test_meso_service_trend_series_with_seed_data():
    app = create_app('testing')
    with app.app_context():
        repo = MesoRepository()
        # seed some data
        repo.upsert_trend_scores([
            {"symbol": "^GSPC", "date": "2024-01-01", "score": 55.0, "components_json": None},
            {"symbol": "^GSPC", "date": "2024-01-02", "score": 60.0, "components_json": None},
        ])
        repo.upsert_index_prices([
            {"symbol": "^GSPC", "date": "2024-01-01", "close": 4800.0, "currency": "USD", "close_usd": 4800.0},
            {"symbol": "^GSPC", "date": "2024-01-02", "close": 4820.0, "currency": "USD", "close_usd": 4820.0},
        ])

        svc = MesoService()
        out = svc.get_trend_series('^GSPC', window='3y', currency='USD')
        assert out['symbol'] == '^GSPC'
        assert len(out['scores']) >= 2
        assert len(out['prices']) >= 2


def test_meso_service_compare_series_with_seed_data():
    app = create_app('testing')
    with app.app_context():
        repo = MesoRepository()
        repo.upsert_trend_scores([
            {"symbol": "^GSPC", "date": "2024-01-01", "score": 55.0, "components_json": None},
            {"symbol": "^NDX", "date": "2024-01-01", "score": 65.0, "components_json": None},
        ])
        svc = MesoService()
        cmp_out = svc.get_compare_series(['^GSPC', '^NDX'], window='1y', currency='USD')
        assert cmp_out['symbols'] == ['^GSPC', '^NDX']
        assert isinstance(cmp_out['series'].get('^GSPC'), list)
        assert isinstance(cmp_out['series'].get('^NDX'), list)


