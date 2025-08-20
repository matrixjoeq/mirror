#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场数据Provider（真实数据-only）：
- 不再提供任何样例/兜底数据（包括测试环境）。
- 仅实现必要接口：fetch_commodities_latest, fetch_fx_latest。
"""

from __future__ import annotations

from typing import List, Dict

from ..macro_config import COMMODITIES, FX_PAIRS, ENABLE_NETWORK, FORCE_SAMPLE_ONLY
from .worldbank_provider import fetch_macro_latest as wb_fetch_macro_latest  # noqa: F401
from .ecb_fx_provider import fetch_fx_latest_frankfurter


def fetch_commodities_latest(symbols: List[str] | None = None) -> List[Dict]:
    # 尚未接入真实商品数据源，按约定返回空；不提供样例数据
    _ = symbols or COMMODITIES
    return []


def fetch_fx_latest(pairs: List[str] | None = None) -> List[Dict]:
    ps = pairs or FX_PAIRS
    # 仅返回真实 Frankfurter 数据；失败则返回空（测试环境也不再兜底样本）
    try:
        data = fetch_fx_latest_frankfurter(ps)
        if data:
            return data
    except Exception:
        pass
    return []


