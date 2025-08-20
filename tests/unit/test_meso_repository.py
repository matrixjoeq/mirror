#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import create_app
from services.meso_repository import MesoRepository


def test_meso_repository_crud_prices_and_scores():
    app = create_app('testing')
    with app.app_context():
        repo = MesoRepository()

        # upsert prices
        n1 = repo.upsert_index_prices([
            {"symbol": "^GSPC", "date": "2024-12-30", "close": 4800.0, "currency": "USD", "close_usd": 4800.0},
            {"symbol": "^GSPC", "date": "2024-12-31", "close": 4820.0, "currency": "USD", "close_usd": 4820.0},
        ])
        assert n1 >= 1
        prices = repo.fetch_prices("^GSPC")
        assert len(prices) >= 2
        assert prices[-1]["close_usd"] == 4820.0

        # upsert scores
        n2 = repo.upsert_trend_scores([
            {"symbol": "^GSPC", "date": "2024-12-30", "score": 55.5, "components_json": None},
            {"symbol": "^GSPC", "date": "2024-12-31", "score": 60.0, "components_json": None},
        ])
        assert n2 >= 1
        scores = repo.fetch_scores("^GSPC")
        assert len(scores) >= 2
        assert scores[-1]["score"] == 60.0

        # refresh meta
        repo.record_refresh("prices", "2024-12-31T23:59:59Z", 2)


