#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import types
from app import create_app


def _install_fake_provider():
    fake = types.ModuleType('services.data_providers.meso_market_provider')

    def fetch_index_history(symbols, period='3y'):
        return {s: [{"date": "2024-01-01", "close": 100.0}] for s in symbols}

    def fetch_fx_timeseries_to_usd(quote_list, start_date, end_date):
        return {"2024-01-01": {"USD": 1.0, "EUR": 1.1, "JPY": 0.009}}

    fake.fetch_index_history = fetch_index_history
    fake.fetch_fx_timeseries_to_usd = fetch_fx_timeseries_to_usd
    sys.modules['services.data_providers.meso_market_provider'] = fake


def test_meso_dashboard_and_apis_after_refresh():
    app = create_app('testing')
    _install_fake_provider()
    client = app.test_client()

    # refresh with 3 indexes covering USD/EUR/JPY
    r = client.post('/api/meso/refresh?period=1y', json={"symbols": ['^GSPC', '^STOXX50E', '^N225']})
    assert r.status_code == 200
    assert r.get_json().get('success') is True

    # dashboard page
    rp = client.get('/meso')
    assert rp.status_code == 200
    html = rp.get_data(as_text=True)
    assert '^GSPC' in html

    # APIs
    r1 = client.get('/api/meso/indexes')
    assert r1.status_code == 200
    r2 = client.get('/api/meso/trend_series?symbol=%5ESTOXX50E')
    assert r2.status_code == 200
    r3 = client.get('/api/meso/compare_series?symbols=%5EGSPC,%5ESTOXX50E,%5EN225')
    assert r3.status_code == 200


