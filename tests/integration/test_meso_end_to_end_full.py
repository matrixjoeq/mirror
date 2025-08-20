#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import types
from app import create_app
from services.meso_repository import MesoRepository


def _install_fake_provider():
    fake = types.ModuleType('services.data_providers.meso_market_provider')

    def fetch_index_history(symbols, period='3y'):
        # enough rows to produce scores (>=63 trading days)
        base = [{"date": "2024-01-01", "close": 100.0}]
        base += [{"date": f"2024-03-{i:02d}", "close": 100.0 + i} for i in range(1, 70)]
        return {s: base for s in symbols}

    def fetch_fx_timeseries_to_usd(quote_list, start_date, end_date):
        # flat 1.0 for simplicity across days (plus ensure EUR/JPY exist)
        days = ["2024-01-01"] + [f"2024-03-{i:02d}" for i in range(1, 70)]
        return {d: {"USD": 1.0, "EUR": 1.1, "JPY": 0.009} for d in days}

    fake.fetch_index_history = fetch_index_history
    fake.fetch_fx_timeseries_to_usd = fetch_fx_timeseries_to_usd
    sys.modules['services.data_providers.meso_market_provider'] = fake


def test_meso_end_to_end_refresh_persist_and_pages():
    app = create_app('testing')
    _install_fake_provider()
    client = app.test_client()

    # refresh
    r = client.post('/api/meso/refresh?period=1y', json={"symbols": ['^GSPC', '^STOXX50E', '^N225']})
    assert r.status_code == 200
    assert r.get_json().get('success') is True

    # repository has data
    with app.app_context():
        repo = MesoRepository()
        assert len(repo.fetch_prices('^GSPC')) > 0
        assert len(repo.fetch_scores('^GSPC')) > 0

    # page and apis
    assert client.get('/meso').status_code == 200
    assert client.get('/api/meso/compare_series?symbols=%5EGSPC,%5ESTOXX50E').status_code == 200
    assert client.get('/api/meso/trend_series?symbol=%5EGSPC').status_code == 200


