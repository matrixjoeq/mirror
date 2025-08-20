#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import types
import sys


def test_worldbank_provider_success(monkeypatch):
    from services.data_providers import worldbank_provider as mod

    # stub requests.get
    class FakeResp:
        def __init__(self, payload):
            self._payload = payload
        def json(self):
            return self._payload
        def raise_for_status(self):
            return None

    def fake_get(url, timeout=10):
        # return minimal WB structure: [meta, rows]
        return FakeResp([
            {"total": 1},
            [
                {"countryiso3code": "USA", "date": "2024", "value": 3.2},
                {"countryiso3code": "DEU", "date": "2024", "value": 2.6},
            ],
        ])

    monkeypatch.setattr(mod.requests, 'get', fake_get)

    rows = mod.fetch_macro_latest(["US", "DE"], ["cpi_yoy"])
    assert any(r['economy'] == 'US' for r in rows)
    assert any(r['economy'] == 'DE' for r in rows)


