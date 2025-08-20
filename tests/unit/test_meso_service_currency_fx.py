#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import types
from app import create_app
from services.meso_service import MesoService
from services.meso_repository import MesoRepository


def _install_fake_provider_fx():
    fake = types.ModuleType('services.data_providers.meso_market_provider')

    def fetch_index_history(symbols, period='3y'):
        out = {}
        for s in symbols:
            # two dates so 63d window isn't satisfied -> only prices checked in this test
            out[s] = [
                {"date": "2024-01-01", "close": 100.0},
                {"date": "2024-01-02", "close": 110.0},
            ]
        return out

    def fetch_fx_timeseries_to_usd(quote_list, start_date, end_date):
        # Provide different FX for EUR/JPY on the same dates
        return {
            "2024-01-01": {"USD": 1.0, "EUR": 1.2, "JPY": 0.009},
            "2024-01-02": {"USD": 1.0, "EUR": 1.25, "JPY": 0.0091},
        }

    fake.fetch_index_history = fetch_index_history
    fake.fetch_fx_timeseries_to_usd = fetch_fx_timeseries_to_usd
    sys.modules['services.data_providers.meso_market_provider'] = fake


def test_refresh_uses_historical_fx_per_day_for_usd_close():
    app = create_app('testing')
    with app.app_context():
        _install_fake_provider_fx()
        repo = MesoRepository()
        svc = MesoService()
        # Choose one EUR and one JPY index to exercise FX paths
        res = svc.refresh_prices_and_scores(symbols=['^STOXX50E', '^N225'], period='1y')
        assert res['refreshed'] is True
        # Verify close_usd is computed from per-day FX
        eur_prices = repo.fetch_prices('^STOXX50E')
        jpy_prices = repo.fetch_prices('^N225')
        # First day
        eur_day1 = next(p for p in eur_prices if p['date'] == '2024-01-01')
        jpy_day1 = next(p for p in jpy_prices if p['date'] == '2024-01-01')
        assert abs(eur_day1['close_usd'] - (100.0 * 1.2)) < 1e-9
        assert abs(jpy_day1['close_usd'] - (100.0 * 0.009)) < 1e-9
        # Second day
        eur_day2 = next(p for p in eur_prices if p['date'] == '2024-01-02')
        jpy_day2 = next(p for p in jpy_prices if p['date'] == '2024-01-02')
        assert abs(eur_day2['close_usd'] - (110.0 * 1.25)) < 1e-9
        assert abs(jpy_day2['close_usd'] - (110.0 * 0.0091)) < 1e-9


