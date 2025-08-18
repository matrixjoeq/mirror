#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场数据Provider（MVP）：
- 目标：优先返回真实数据；无法联网或失败时回退样本。
- 仅实现必要接口：fetch_commodities_latest, fetch_fx_latest
"""

from __future__ import annotations

from typing import List, Dict

from ..macro_config import COMMODITIES, FX_PAIRS, ENABLE_NETWORK, FORCE_SAMPLE_ONLY
from .worldbank_provider import fetch_macro_latest as wb_fetch_macro_latest  # noqa: F401
from .ecb_fx_provider import fetch_fx_latest_frankfurter


def fetch_commodities_latest(symbols: List[str] | None = None) -> List[Dict]:
    syms = symbols or COMMODITIES
    if not FORCE_SAMPLE_ONLY and ENABLE_NETWORK:
        try:
            # 预留：可接入 yfinance 或其他免费源
            # 为避免引新依赖，MVP 暂直接回退
            raise RuntimeError("network provider not implemented yet")
        except Exception:
            pass
    # 样本回退
    data = []
    for s in syms:
        if s == "brent":
            val = 78.2
        elif s == "wti":
            val = 74.9
        elif s == "natgas":
            val = 2.2
        elif s == "gold":
            val = 2100.0
        elif s == "silver":
            val = 24.5
        elif s == "copper":
            val = 3.9
        else:
            val = 0.0
        data.append({"commodity": s, "date": "latest", "value": val, "currency": "USD", "provider": "sample"})
    return data


def fetch_fx_latest(pairs: List[str] | None = None) -> List[Dict]:
    ps = pairs or FX_PAIRS
    if not FORCE_SAMPLE_ONLY and ENABLE_NETWORK:
        try:
            data = fetch_fx_latest_frankfurter(ps)
            if data:
                return data
        except Exception:
            pass
    # 样本回退
    results: List[Dict] = []
    for p in ps:
        if p == "EURUSD":
            price = 1.08
        elif p == "USDJPY":
            price = 150.0
        else:
            price = 1.0
        results.append({"pair": p, "date": "latest", "price": price, "provider": "sample"})
    return results


