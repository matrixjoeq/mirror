#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile

from services.database_service import DatabaseService
from services.macro_repository import MacroRepository


def _tmp_db() -> str:
    fd, path = tempfile.mkstemp(prefix="macro_repo_edges_", suffix=".db")
    os.close(fd)
    return path


def test_empty_bulk_calls_and_has_any_data():
    db_path = _tmp_db()
    try:
        db = DatabaseService(db_path)
        repo = MacroRepository(db)
        assert repo.bulk_upsert_macro_series([]) == 0
        assert repo.bulk_upsert_commodity_series([]) == 0
        assert repo.bulk_upsert_fx_series([]) == 0
        assert repo.has_any_data() is False
    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


