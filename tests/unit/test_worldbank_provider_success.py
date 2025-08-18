#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from unittest import mock

from services.data_providers.worldbank_provider import fetch_macro_latest


class DummyResp:
    def __init__(self, payload: str):
        self._p = payload.encode("utf-8")
    def read(self):
        return self._p
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False


def test_worldbank_success_and_failure_paths():
    # failure path: exception -> empty
    with mock.patch("services.data_providers.worldbank_provider.urllib.request.urlopen", side_effect=Exception("net")):
        out = fetch_macro_latest(["US"], ["cpi_yoy"])
        assert out == []

    # success path: valid JSON array & series
    payload = '[{"page":1},[{"date":"2024","value":3.2},{"date":"2023","value":2.8}]]'
    with mock.patch("services.data_providers.worldbank_provider.urllib.request.urlopen", return_value=DummyResp(payload)):
        rows = fetch_macro_latest(["US"], ["cpi_yoy"])
        assert isinstance(rows, list) and len(rows) >= 1
        r0 = rows[0]
        assert r0["economy"] == "US" and r0["indicator"] == "cpi_yoy"
        assert r0["date"].startswith("2024")
        assert isinstance(r0["value"], float)


