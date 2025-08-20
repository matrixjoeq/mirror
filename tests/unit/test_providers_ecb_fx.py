#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from types import SimpleNamespace


def test_ecb_fx_provider_fetch_latest_frankfurter(monkeypatch):
    from services.data_providers import ecb_fx_provider as mod

    class FakeResp:
        def __init__(self, data):
            self._data = data
        def read(self):
            return json.dumps(self._data).encode('utf-8')

    def fake_urlopen(url, timeout=6.0):
        data = {"date": "2024-01-01", "rates": {"USD": 1.1, "JPY": 160.0}}
        return FakeResp(data)

    monkeypatch.setattr(mod.urllib.request, 'urlopen', fake_urlopen)

    out = mod.fetch_fx_latest_frankfurter(["EURUSD", "USDJPY"])
    pairs = {r['pair']: r['price'] for r in out}
    assert 'EURUSD' in pairs and abs(pairs['EURUSD'] - 1.1) < 1e-9
    assert 'USDJPY' in pairs and abs(pairs['USDJPY'] - (160.0 / 1.1)) < 1e-9


