#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile

from services.database_service import DatabaseService
from services.macro_service import MacroService


def _tmp_db() -> str:
    fd, path = tempfile.mkstemp(prefix="macro_score_", suffix=".db")
    os.close(fd)
    return path


def test_scoring_value_zscore_percentile_paths():
    db_path = _tmp_db()
    try:
        db = DatabaseService(db_path)
        svc = MacroService(db)
        # seed deterministic values to exercise three methods
        with db.get_connection() as conn:
            cur = conn.cursor()
            # cpi_yoy: US 4, DE 2 -> 方向-1
            cur.execute("INSERT OR REPLACE INTO macro_series (economy, indicator, date, value, provider, revised_at) VALUES (?,?,?,?,?,?)", ("US","cpi_yoy","2024-12-31",4.0,"t",None))
            cur.execute("INSERT OR REPLACE INTO macro_series (economy, indicator, date, value, provider, revised_at) VALUES (?,?,?,?,?,?)", ("DE","cpi_yoy","2024-12-31",2.0,"t",None))
            # unemployment: US 4, DE 5 -> 方向-1（US 更优）
            cur.execute("INSERT OR REPLACE INTO macro_series (economy, indicator, date, value, provider, revised_at) VALUES (?,?,?,?,?,?)", ("US","unemployment","2024-12-31",4.0,"t",None))
            cur.execute("INSERT OR REPLACE INTO macro_series (economy, indicator, date, value, provider, revised_at) VALUES (?,?,?,?,?,?)", ("DE","unemployment","2024-12-31",5.0,"t",None))
            # gdp_yoy: US 2.5, DE 1.0 -> 方向+1（US 更优）
            cur.execute("INSERT OR REPLACE INTO macro_series (economy, indicator, date, value, provider, revised_at) VALUES (?,?,?,?,?,?)", ("US","gdp_yoy","2024-12-31",2.5,"t",None))
            cur.execute("INSERT OR REPLACE INTO macro_series (economy, indicator, date, value, provider, revised_at) VALUES (?,?,?,?,?,?)", ("DE","gdp_yoy","2024-12-31",1.0,"t",None))
            conn.commit()

        for view in ("value", "zscore", "percentile"):
            snap = svc.get_snapshot(view=view, date="2025-01-01", window="1y")
            assert snap["view"] == view
            assert set(snap["economies"]) >= {"US","DE"}
            # US 应不差于 DE（大多数口径下 US 更优）
            us = next(x for x in snap["ranking"] if x["economy"] == "US")["score"]
            de = next(x for x in snap["ranking"] if x["economy"] == "DE")["score"]
            assert us >= de
    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


