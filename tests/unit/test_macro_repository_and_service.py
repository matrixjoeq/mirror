#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile

from services.database_service import DatabaseService
from services.macro_repository import MacroRepository
from services.macro_service import MacroService
from services.macro_config import INDICATORS
from services.data_providers.market_provider import fetch_commodities_latest, fetch_fx_latest
from typing import Dict


def _tmp_db() -> str:
    fd, path = tempfile.mkstemp(prefix="macro_repo_srv_", suffix=".db")
    os.close(fd)
    return path


def test_repository_upsert_fetch_and_flags():
    db_path = _tmp_db()
    try:
        db = DatabaseService(db_path)
        repo = MacroRepository(db)
        assert not repo.has_any_data()

        rows = [
            {"economy": "US", "indicator": "cpi_yoy", "date": "2024-12-01", "value": 3.4, "provider": "t", "revised_at": None},
            {"economy": "US", "indicator": "unemployment", "date": "2024-12-01", "value": 3.9, "provider": "t", "revised_at": None},
            {"economy": "DE", "indicator": "cpi_yoy", "date": "2024-12-01", "value": 3.2, "provider": "t", "revised_at": None},
        ]
        count = repo.bulk_upsert_macro_series(rows)
        assert count >= 3
        assert repo.has_any_data()

        # also upsert commodity and fx
        c = repo.bulk_upsert_commodity_series([
            {"commodity": "brent", "date": "2024-12-01", "value": 78.2, "currency": "USD", "provider": "t"}
        ])
        f = repo.bulk_upsert_fx_series([
            {"pair": "EURUSD", "date": "2024-12-01", "price": 1.08}
        ])
        assert c >= 1 and f >= 1

        us = repo.fetch_macro_series_by_economy("us")
        assert "cpi_yoy" in us and "unemployment" in us
        assert us["cpi_yoy"][0]["value"] == 3.4

        # latest by indicator
        latest: Dict[str, float] = repo.fetch_latest_by_indicator("cpi_yoy")
        assert isinstance(latest, dict) and latest.get("US") == 3.4

        # upsert a score and verify written
        repo.upsert_score("value", "macro", "US", "2024-12-01", 88.5, components_json=None)
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT score FROM scores WHERE view = ? AND entity_type = ? AND entity_id = ?", ("value", "macro", "US"))
            row = cur.fetchone()
            assert row is not None and float(row[0]) == 88.5
        # idempotent upsert should not error
        count2 = repo.bulk_upsert_macro_series(rows)
        assert count2 >= 1
    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


def test_service_seed_snapshot_country_score():
    db_path = _tmp_db()
    try:
        db = DatabaseService(db_path)
        svc = MacroService(db)

        # first snapshot should seed data automatically
        snap = svc.get_snapshot(view="value", date="2025-01-01", window="6m")
        assert snap["view"] == "value"
        assert snap["window"] == "6m"
        assert len(snap["economies"]) == 5
        assert len(snap["ranking"]) == 5
        # at least one economy should have positive score after seed
        assert any(item["score"] >= 0 for item in snap["ranking"])

        country = svc.get_country("US", window="1y")
        assert country["economy"] == "US"
        assert isinstance(country["series"], dict)
        assert len(country["composite_score"]) == 1
        assert country["composite_score"][0]["value"] >= 0

        s1 = svc.get_score("commodity", "gold", view="trend")
        assert s1["score"] == 60.0
        s2 = svc.get_score("etf", "spy", view="trend")
        assert s2["score"] == 50.0

        # trigger refresh (should upsert commodity/fx via sample fallback)
        ref = svc.refresh_all()
        assert ref.get("refreshed") is True
        # verify commodity/fx written
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(1) FROM commodity_series")
            assert int(cur.fetchone()[0]) >= 1
            cur.execute("SELECT COUNT(1) FROM fx_series")
            assert int(cur.fetchone()[0]) >= 1

        # indicator config should expose directions
        assert "cpi_yoy" in INDICATORS and isinstance(INDICATORS["cpi_yoy"][0], int)

        # provider stubs should return non-empty sample lists in tests (no network)
        assert isinstance(fetch_commodities_latest(), list)
        assert isinstance(fetch_fx_latest(), list)
    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


