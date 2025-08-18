#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile

from services.database_service import DatabaseService
from services.macro_repository import MacroRepository
from services.data_providers.market_provider import fetch_fx_latest, fetch_commodities_latest
from services.data_providers.worldbank_provider import fetch_macro_latest
from services.data_providers.ecb_fx_provider import fetch_fx_latest_frankfurter
from unittest import mock


def _tmp_db() -> str:
    fd, path = tempfile.mkstemp(prefix="macro_repo_read_", suffix=".db")
    os.close(fd)
    return path


def test_repo_read_latest_by_indicator_and_seed_paths():
    db_path = _tmp_db()
    try:
        db = DatabaseService(db_path)
        repo = MacroRepository(db)
        # upsert two economies with same indicator across two dates
        repo.bulk_upsert_macro_series([
            {"economy": "US", "indicator": "cpi_yoy", "date": "2023-12-31", "value": 3.9, "provider": "t", "revised_at": None},
            {"economy": "US", "indicator": "cpi_yoy", "date": "2024-12-31", "value": 3.4, "provider": "t", "revised_at": None},
            {"economy": "DE", "indicator": "cpi_yoy", "date": "2024-12-31", "value": 3.2, "provider": "t", "revised_at": None},
        ])
        latest = repo.fetch_latest_by_indicator("cpi_yoy")
        assert latest["US"] == 3.4 and latest["DE"] == 3.2
    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


def test_provider_stubs_no_network_ok():
    # Market provider should return samples in test env
    fx = fetch_fx_latest()
    com = fetch_commodities_latest()
    assert isinstance(fx, list) and isinstance(com, list)
    # WB fetch should tolerate unknown indicator and simply return empty
    rows = fetch_macro_latest(["US"], ["unknown_indicator"])  # expect []
    assert isinstance(rows, list)

    # mock frankfurter path to raise and then to return
    with mock.patch("services.data_providers.ecb_fx_provider.urllib.request.urlopen", side_effect=Exception("net")):
        assert fetch_fx_latest_frankfurter(["EURUSD"]) == []
    class DummyResp:
        def __init__(self, payload: str):
            self._p = payload.encode("utf-8")
        def read(self):
            return self._p
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
    payload = '{"amount":1,"base":"EUR","date":"2025-01-01","rates":{"USD":1.1,"JPY":165.0}}'
    with mock.patch("services.data_providers.ecb_fx_provider.urllib.request.urlopen", return_value=DummyResp(payload)):
        data = fetch_fx_latest_frankfurter(["EURUSD","USDJPY"]) 
        assert any(x.get("pair")=="EURUSD" for x in data)
        assert any(x.get("pair")=="USDJPY" for x in data)


