#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ECB 汇率 Provider (MVP)

抓取常见货币对最新价格：
- EURUSD（以 ECB EUR base 报价转换）
- USDJPY（需要反转或使用其他免费源；此处演示用简单映射，实际可切换到 frankfurter.app）

默认使用 frankfurter.app 免费API（ECB数据镜像），失败交由调用方兜底。
"""

from __future__ import annotations

import json
import urllib.request
from typing import List, Dict


def fetch_fx_latest_frankfurter(pairs: List[str], timeout: float = 6.0) -> List[Dict]:
    """使用 frankfurter.app 获取最新 FX（基于 ECB）。
    仅支持常见对，超出范围可在上层样本兜底。
    """
    results: List[Dict] = []
    # frankfurter 基础：最新（EUR基准）
    try:
        with urllib.request.urlopen("https://api.frankfurter.app/latest", timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return results

    rates = data.get("rates") or {}
    # EURUSD = rates["USD"]
    # USDJPY = 1 / (rates["USD"] / rates["JPY"]) = rates["JPY"]/rates["USD"]
    usd = float(rates.get("USD") or 0)
    jpy = float(rates.get("JPY") or 0)
    for p in pairs:
        if p == "EURUSD" and usd > 0:
            results.append({"pair": "EURUSD", "date": data.get("date", "latest"), "price": usd, "provider": "ecb"})
        elif p == "USDJPY" and usd > 0 and jpy > 0:
            results.append({"pair": "USDJPY", "date": data.get("date", "latest"), "price": jpy / usd, "provider": "ecb"})
    return results


