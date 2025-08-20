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
        return {"2024-01-01": {"USD": 1.0}}

    fake.fetch_index_history = fetch_index_history
    fake.fetch_fx_timeseries_to_usd = fetch_fx_timeseries_to_usd
    sys.modules['services.data_providers.meso_market_provider'] = fake


def test_meso_refresh_api_works_with_stub_provider():
    app = create_app('testing')
    _install_fake_provider()
    client = app.test_client()
    r = client.post('/api/meso/refresh', json={"symbols": ["^GSPC", "^NDX"]})
    assert r.status_code == 200
    body = r.get_json()
    assert body['success'] is True
    assert set(body['data']['symbols']) == {"^GSPC", "^NDX"}


