#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import create_app
from services.meso_repository import MesoRepository


def test_meso_repository_latest_and_range_queries():
    app = create_app('testing')
    with app.app_context():
        repo = MesoRepository()

        # seed prices for two symbols
        repo.upsert_index_prices([
            {"symbol": "^GSPC", "date": "2024-01-01", "close": 100.0, "currency": "USD", "close_usd": 100.0},
            {"symbol": "^GSPC", "date": "2024-01-02", "close": 110.0, "currency": "USD", "close_usd": 110.0},
            {"symbol": "^NDX", "date": "2024-01-01", "close": 150.0, "currency": "USD", "close_usd": 150.0},
        ])

        assert repo.get_latest_price_date('^GSPC') == '2024-01-02'
        assert repo.get_latest_price_date('^NDX') == '2024-01-01'

        # fetch range (start)
        pr_all = repo.fetch_prices('^GSPC')
        pr_from = repo.fetch_prices('^GSPC', start='2024-01-02')
        assert len(pr_all) == 2
        assert len(pr_from) == 1 and pr_from[0]['date'] == '2024-01-02'

        # seed scores
        repo.upsert_trend_scores([
            {"symbol": "^GSPC", "date": "2024-01-01", "score": 55.0, "components_json": None},
            {"symbol": "^GSPC", "date": "2024-01-02", "score": 60.0, "components_json": None},
        ])
        assert repo.get_latest_score_date('^GSPC') == '2024-01-02'
        sc_from = repo.fetch_scores('^GSPC', start='2024-01-02')
        assert len(sc_from) == 1 and sc_from[0]['date'] == '2024-01-02'

        # record refresh meta and verify
        repo.record_refresh('meso', '2024-01-02T00:00:00Z', 3)
        with repo.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM refresh_meta WHERE source=?', ('meso',))
            cnt = cur.fetchone()[0]
            assert cnt >= 1


