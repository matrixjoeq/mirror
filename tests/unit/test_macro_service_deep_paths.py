#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
from typing import List, Dict
from unittest import mock

from services.database_service import DatabaseService
from services.macro_service import MacroService


def _tmp_db() -> str:
    fd, path = tempfile.mkstemp(prefix="macro_service_deep_", suffix=".db")
    os.close(fd)
    return path


def test_snapshot_span_zero_and_missing_indicators_and_ordering():
    db_path = _tmp_db()
    try:
        db = DatabaseService(db_path)
        svc = MacroService(db)
        # seed two economies same value to trigger span == 0 path for one indicator
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO macro_series (economy, indicator, date, value, provider, revised_at) VALUES (?,?,?,?,?,?)",
                ("US", "cpi_yoy", "2024-12-31", 3.0, "t", None),
            )
            cur.execute(
                "INSERT OR REPLACE INTO macro_series (economy, indicator, date, value, provider, revised_at) VALUES (?,?,?,?,?,?)",
                ("DE", "cpi_yoy", "2024-12-31", 3.0, "t", None),
            )
            conn.commit()
        snap = svc.get_snapshot(view="value", date="2025-01-01", window="1y")
        assert snap["window"] == "1y"
        assert "ranking" in snap and isinstance(snap["ranking"], list)
        # equal values -> indicator contributes nothing; still returns valid structure
        for item in snap["ranking"]:
            assert "economy" in item and "score" in item

    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


def test_refresh_all_with_provider_exceptions_and_success_paths():
    db_path = _tmp_db()
    try:
        db = DatabaseService(db_path)
        svc = MacroService(db)

        # first call with providers raising -> should be handled
        with mock.patch("services.macro_service.fetch_commodities_latest", side_effect=RuntimeError("boom")):
            with mock.patch("services.macro_service.fetch_fx_latest", side_effect=ValueError("bad")):
                with mock.patch("services.macro_service.wb_fetch_macro_latest", side_effect=RuntimeError("wb")):
                    out = svc.refresh_all()
                    assert out.get("refreshed") is True

        # second call with successful providers
        fake_com = [{"commodity": "brent", "date": "2025-01-01", "value": 80.0, "currency": "USD", "provider": "x"}]
        fake_fx = [{"pair": "EURUSD", "date": "2025-01-01", "price": 1.1}]
        fake_wb = [
            {"economy": "US", "indicator": "unemployment", "date": "2024-12-31", "value": 4.0, "provider": "worldbank", "revised_at": None}
        ]
        with mock.patch("services.macro_service.fetch_commodities_latest", return_value=fake_com):
            with mock.patch("services.macro_service.fetch_fx_latest", return_value=fake_fx):
                with mock.patch("services.macro_service.wb_fetch_macro_latest", return_value=fake_wb):
                    out2 = svc.refresh_all()
                    assert out2.get("refreshed") is True
        # verify writes
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(1) FROM commodity_series")
            assert int(cur.fetchone()[0]) >= 1
            cur.execute("SELECT COUNT(1) FROM fx_series")
            assert int(cur.fetchone()[0]) >= 1
            cur.execute("SELECT COUNT(1) FROM macro_series WHERE indicator='unemployment'")
            assert int(cur.fetchone()[0]) >= 1

    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


