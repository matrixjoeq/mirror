#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
World Bank Provider (MVP)

抓取宏观指标最新数据（按经济体/指标），失败回退由调用方处理。

指标映射（示例）：
- cpi_yoy -> FP.CPI.TOTL.ZG（消费价格指数年度同比，%）
- unemployment -> SL.UEM.TOTL.ZS（失业率，总计，%）
- gdp_yoy -> NY.GDP.MKTP.KD.ZG（GDP 实际增长率，%）

注：PMI等未在WB免费标准库中提供，后续可补其他源。
"""

from __future__ import annotations

import json
import urllib.request
from typing import Dict, List, Tuple


WB_COUNTRY_CODE: Dict[str, str] = {
    "US": "USA",
    "DE": "DEU",
    "JP": "JPN",
    "CN": "CHN",
    "HK": "HKG",
}

WB_INDICATOR_CODE: Dict[str, str] = {
    "cpi_yoy": "FP.CPI.TOTL.ZG",
    "unemployment": "SL.UEM.TOTL.ZS",
    "gdp_yoy": "NY.GDP.MKTP.KD.ZG",
}


def _wb_url(country_code: str, indicator_code: str, per_page: int = 60) -> str:
    # 返回 JSON 格式，按日期倒序查询（WB默认已按日期）
    return (
        f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator_code}"
        f"?format=json&per_page={per_page}"
    )


def fetch_macro_latest(economies: List[str], indicators: List[str], timeout: float = 8.0) -> List[Dict]:
    """抓取各经济体-指标的最近一期非空值，返回 macro_series 兼容记录列表。

    记录字段：economy, indicator, date(YYYY-MM-DD), value, provider
    """
    results: List[Dict] = []
    for eco in economies:
        ccode = WB_COUNTRY_CODE.get(eco)
        if not ccode:
            continue
        for ind in indicators:
            icode = WB_INDICATOR_CODE.get(ind)
            if not icode:
                continue
            url = _wb_url(ccode, icode)
            try:
                with urllib.request.urlopen(url, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception:
                continue

            # WB JSON: [metadata, [ {"date": "2024", "value": 3.2, ...}, ... ]]
            if not isinstance(data, list) or len(data) < 2 or not isinstance(data[1], list):
                continue
            series = data[1]
            latest = None
            for item in series:
                val = item.get("value")
                if val is not None:
                    latest = item
                    break
            if latest is None:
                continue
            year = str(latest.get("date") or "")
            # WB年度数据仅给年份，这里拼接到年底日期
            date_str = f"{year}-12-31" if len(year) == 4 else year
            try:
                value_f = float(latest.get("value"))
            except Exception:
                continue
            results.append(
                {
                    "economy": eco,
                    "indicator": ind,
                    "date": date_str,
                    "value": value_f,
                    "provider": "worldbank",
                    "revised_at": None,
                }
            )
    return results


