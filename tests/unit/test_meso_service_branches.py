#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import types
from app import create_app
from services.meso_service import MesoService
from services.meso_repository import MesoRepository


def _install_provider_empty():
    fake = types.ModuleType('services.data_providers.meso_market_provider')

    def fetch_index_history(symbols, period='3y'):
        return {}

    def fetch_fx_timeseries_to_usd(quote_list, start_date, end_date):
        return {}

    fake.fetch_index_history = fetch_index_history
    fake.fetch_fx_timeseries_to_usd = fetch_fx_timeseries_to_usd
    sys.modules['services.data_providers.meso_market_provider'] = fake


def _install_provider_for_incremental_and_clipping():
    fake = types.ModuleType('services.data_providers.meso_market_provider')

    def fetch_index_history(symbols, period='3y'):
        out = {}
        for s in symbols:
            # include an old date (to be skipped) and enough points for 63d window
            rows = [{"date": "2024-01-01", "close": 100.0}]
            rows += [{"date": f"2024-03-{i:02d}", "close": 100.0 + i} for i in range(1, 65)]
            # add extreme last point to trigger clipping: v0=100, v=60 -> score=0; later v=160 -> score=100
            rows.append({"date": "2024-06-15", "close": 60.0})
            rows.append({"date": "2024-06-16", "close": 160.0})
            out[s] = rows
        return out

    def fetch_fx_timeseries_to_usd(quote_list, start_date, end_date):
        # flat 1.0 across a wide date range
        days = ["2024-01-01"] + [f"2024-03-{i:02d}" for i in range(1, 65)] + ["2024-06-15", "2024-06-16"]
        return {d: {"USD": 1.0, "EUR": 1.1, "JPY": 0.009} for d in days}

    fake.fetch_index_history = fetch_index_history
    fake.fetch_fx_timeseries_to_usd = fetch_fx_timeseries_to_usd
    sys.modules['services.data_providers.meso_market_provider'] = fake


def test_refresh_returns_zero_when_no_data():
    app = create_app('testing')
    with app.app_context():
        _install_provider_empty()
        svc = MesoService()
        res = svc.refresh_prices_and_scores(symbols=['^GSPC'], period='1y')
        assert res['refreshed'] is True
        assert res['prices'] == 0
        assert res['scores'] == 0


def test_incremental_skip_and_score_clipping():
    app = create_app('testing')
    with app.app_context():
        _install_provider_for_incremental_and_clipping()
        repo = MesoRepository()
        svc = MesoService()

        # pre-seed a latest date so earlier rows are skipped
        repo.upsert_index_prices([
            {"symbol": "^GSPC", "date": "2024-03-10", "close": 999.0, "currency": "USD", "close_usd": 999.0},
        ])

        res = svc.refresh_prices_and_scores(symbols=['^GSPC'], period='1y')
        assert res['refreshed'] is True
        # ensure some prices inserted (since later than 2024-03-10 exist)
        assert res['prices'] > 0
        # ensure scores computed
        assert res['scores'] > 0

        # check clipping at 0 and 100 present
        scores = repo.fetch_scores('^GSPC')
        vals = [s['score'] for s in scores if s['date'] in ("2024-06-15", "2024-06-16")]
        assert 0.0 in vals and 100.0 in vals


