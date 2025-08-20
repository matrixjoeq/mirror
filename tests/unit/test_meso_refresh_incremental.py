#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import types
from app import create_app
from services.meso_service import MesoService
from services.meso_repository import MesoRepository


def _install_fake_provider_once():
    fake = types.ModuleType('services.data_providers.meso_market_provider')

    # two days of data, second refresh should insert nothing new
    def fetch_index_history(symbols, period='3y'):
        return {s: [{"date": "2024-01-01", "close": 100.0}, {"date": "2024-01-02", "close": 101.0}] for s in symbols}

    def fetch_fx_timeseries_to_usd(quote_list, start_date, end_date):
        return {"2024-01-01": {"USD": 1.0}, "2024-01-02": {"USD": 1.0}}

    fake.fetch_index_history = fetch_index_history
    fake.fetch_fx_timeseries_to_usd = fetch_fx_timeseries_to_usd
    sys.modules['services.data_providers.meso_market_provider'] = fake


def test_incremental_refresh_does_not_duplicate():
    app = create_app('testing')
    with app.app_context():
        _install_fake_provider_once()
        repo = MesoRepository()
        svc = MesoService()
        r1 = svc.refresh_prices_and_scores(symbols=['^GSPC'], period='1y')
        p1 = len(repo.fetch_prices('^GSPC'))
        s1 = len(repo.fetch_scores('^GSPC'))
        r2 = svc.refresh_prices_and_scores(symbols=['^GSPC'], period='1y')
        p2 = len(repo.fetch_prices('^GSPC'))
        s2 = len(repo.fetch_scores('^GSPC'))
        assert p2 == p1 and s2 == s1


