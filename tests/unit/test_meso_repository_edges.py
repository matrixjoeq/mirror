#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from app import create_app
from services.meso_repository import MesoRepository


class TestMesoRepositoryEdges(unittest.TestCase):
    def test_upsert_empty_returns_zero_and_none_values_ok(self):
        app = create_app('testing')
        with app.app_context():
            repo = MesoRepository()
            assert repo.upsert_index_prices([]) == 0
            assert repo.upsert_trend_scores([]) == 0

            n = repo.upsert_index_prices([
                {"symbol": "^GSPC", "date": "2024-01-02", "close": None, "currency": "USD", "close_usd": None},
            ])
            assert n >= 1

            n2 = repo.upsert_trend_scores([
                {"symbol": "^GSPC", "date": "2024-01-02", "score": None, "components_json": None},
            ])
            assert n2 >= 1


    def test_fetch_with_start_filters_results(self):
        app = create_app('testing')
        with app.app_context():
            repo = MesoRepository()
            repo.upsert_index_prices([
                {"symbol": "^GSPC", "date": "2023-12-30", "close": 4700.0, "currency": "USD", "close_usd": 4700.0},
                {"symbol": "^GSPC", "date": "2024-01-01", "close": 4800.0, "currency": "USD", "close_usd": 4800.0},
            ])
            repo.upsert_trend_scores([
                {"symbol": "^GSPC", "date": "2023-12-30", "score": 40.0, "components_json": None},
                {"symbol": "^GSPC", "date": "2024-01-01", "score": 60.0, "components_json": None},
            ])

            prices = repo.fetch_prices("^GSPC", start="2024-01-01")
            scores = repo.fetch_scores("^GSPC", start="2024-01-01")
            assert all(p["date"] >= "2024-01-01" for p in prices)
            assert all(s["date"] >= "2024-01-01" for s in scores)


if __name__ == '__main__':
    unittest.main()


