#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中观观察配置：全球主要股指与其本币。

仅用于真实数据抓取阶段的元数据；列表可按需扩展。
"""

from __future__ import annotations

from typing import List, Dict


INDEX_DEFS: List[Dict[str, str]] = [
    {"symbol": "^DWCF", "name": "DJ U.S. Total Market", "currency": "USD", "region": "Americas", "market": "US"},
    {"symbol": "^NDX", "name": "Nasdaq 100", "currency": "USD", "region": "Americas", "market": "US"},
    {"symbol": "^DJI", "name": "Dow Jones Industrial", "currency": "USD", "region": "Americas", "market": "US"},
    {"symbol": "^STOXX", "name": "STOXX Europe 600", "currency": "EUR", "region": "EMEA", "market": "EU"},
    {"symbol": "^GDAXI", "name": "DAX", "currency": "EUR", "region": "EMEA", "market": "EU"},
    {"symbol": "^FTSE", "name": "FTSE 100", "currency": "GBP", "region": "EMEA", "market": "UK"},
    {"symbol": "^FCHI", "name": "CAC 40", "currency": "EUR", "region": "EMEA", "market": "EU"},
    {"symbol": "^IBEX", "name": "IBEX 35", "currency": "EUR", "region": "EMEA", "market": "EU"},
    {"symbol": "^TOPX", "name": "TOPIX", "currency": "JPY", "region": "APAC", "market": "JP"},
    {"symbol": "^HSCI", "name": "Hang Seng Composite", "currency": "HKD", "region": "APAC", "market": "HK"},
    {"symbol": "000985.CSI", "name": "CSI All Share", "currency": "CNY", "region": "APAC", "market": "CN"},
    {"symbol": "^NSEI", "name": "Nifty 50", "currency": "INR", "region": "APAC", "market": "IN"},
    {"symbol": "^KS11", "name": "KOSPI", "currency": "KRW", "region": "APAC", "market": "KR"},
    {"symbol": "^AXJO", "name": "ASX 200", "currency": "AUD", "region": "APAC", "market": "AU"},
    {"symbol": "^GSPTSE", "name": "S&P/TSX", "currency": "CAD", "region": "Americas", "market": "CA"},
    {"symbol": "^BVSP", "name": "Bovespa", "currency": "BRL", "region": "Americas", "market": "BR"},
]


def index_currency_map() -> Dict[str, str]:
    return {row["symbol"]: row["currency"] for row in INDEX_DEFS}


def market_of(symbol: str) -> str:
    for row in INDEX_DEFS:
        if row.get("symbol") == symbol:
            return row.get("market", "ALL")
    return "ALL"


def benchmark_of(market: str) -> str:
    # 默认基准：US→^GSPC, HK→^HSI, CN→000300.SS, EU→^STOXX50E, JP→^N225, UK→^FTSE
    mapping = {
        "US": "^DWCF",
        "HK": "^HSCI",
        "CN": "000985.CSI",
        "EU": "^STOXX",
        "JP": "^TOPX",
        "UK": "^FTSE",
    }
    return mapping.get(market, "^GSPC")

