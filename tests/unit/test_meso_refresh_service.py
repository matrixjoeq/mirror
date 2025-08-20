#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import types
from app import create_app
from services.meso_service import MesoService
from services.meso_repository import MesoRepository


def _install_fake_provider():
    fake = types.ModuleType('services.data_providers.meso_market_provider')

    def fetch_index_history(symbols, period='3y'):
        out = {}
        for s in symbols:
            out[s] = [
                {"date": "2024-01-01", "close": 100.0},
                {"date": "2024-04-05", "close": 110.0},
                {"date": "2024-04-06", "close": 112.0},
                {"date": "2024-04-07", "close": 115.0},
                # provide enough days to cross 63-day window logic in service
                *[{"date": f"2024-06-{10+i:02d}", "close": 120.0 + i} for i in range(70)],
            ]
        return out

    def fetch_fx_timeseries_to_usd(quote_list, start_date, end_date):
        # 简化：所有日子的 C→USD = 1.0
        days = ["2024-01-01", "2024-04-05", "2024-04-06", "2024-04-07"] + [f"2024-06-{10+i:02d}" for i in range(70)]
        out = {}
        for d in days:
            m = {"USD": 1.0, "EUR": 1.1, "JPY": 0.009}
            for c in quote_list or []:
                m[c] = 1.0
            out[d] = m
        return out

    fake.fetch_index_history = fetch_index_history
    fake.fetch_fx_timeseries_to_usd = fetch_fx_timeseries_to_usd
    sys.modules['services.data_providers.meso_market_provider'] = fake


def test_refresh_prices_and_scores_with_stub_provider():
    app = create_app('testing')
    with app.app_context():
        _install_fake_provider()
        repo = MesoRepository()
        svc = MesoService()
        res = svc.refresh_prices_and_scores(symbols=['^GSPC'], period='1y')
        assert res['refreshed'] is True
        assert res['symbols'] == ['^GSPC']
        # verify data persisted
        prices = repo.fetch_prices('^GSPC')
        scores = repo.fetch_scores('^GSPC')
        assert len(prices) > 0
        assert len(scores) > 0


