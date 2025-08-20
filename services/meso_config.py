#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中观观察配置：全球主要股指与其本币。

仅用于真实数据抓取阶段的元数据；列表可按需扩展。
"""

from __future__ import annotations

from typing import List, Dict


INDEX_DEFS: List[Dict[str, str]] = [
    {"symbol": "^GSPC", "name": "S&P 500", "currency": "USD", "region": "Americas"},
    {"symbol": "^NDX", "name": "Nasdaq 100", "currency": "USD", "region": "Americas"},
    {"symbol": "^DJI", "name": "Dow Jones Industrial", "currency": "USD", "region": "Americas"},
    {"symbol": "^STOXX50E", "name": "Euro STOXX 50", "currency": "EUR", "region": "EMEA"},
    {"symbol": "^GDAXI", "name": "DAX", "currency": "EUR", "region": "EMEA"},
    {"symbol": "^FTSE", "name": "FTSE 100", "currency": "GBP", "region": "EMEA"},
    {"symbol": "^FCHI", "name": "CAC 40", "currency": "EUR", "region": "EMEA"},
    {"symbol": "^IBEX", "name": "IBEX 35", "currency": "EUR", "region": "EMEA"},
    {"symbol": "^N225", "name": "Nikkei 225", "currency": "JPY", "region": "APAC"},
    {"symbol": "^TOPX", "name": "TOPIX", "currency": "JPY", "region": "APAC"},
    {"symbol": "^HSI", "name": "Hang Seng", "currency": "HKD", "region": "APAC"},
    {"symbol": "000300.SS", "name": "CSI 300", "currency": "CNY", "region": "APAC"},
    {"symbol": "^NSEI", "name": "Nifty 50", "currency": "INR", "region": "APAC"},
    {"symbol": "^KS11", "name": "KOSPI", "currency": "KRW", "region": "APAC"},
    {"symbol": "^AXJO", "name": "ASX 200", "currency": "AUD", "region": "APAC"},
    {"symbol": "^GSPTSE", "name": "S&P/TSX", "currency": "CAD", "region": "Americas"},
    {"symbol": "^BVSP", "name": "Bovespa", "currency": "BRL", "region": "Americas"},
]


def index_currency_map() -> Dict[str, str]:
    return {row["symbol"]: row["currency"] for row in INDEX_DEFS}


