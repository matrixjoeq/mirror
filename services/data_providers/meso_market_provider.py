#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实数据 Provider（中观）：
- 指数价格：yfinance
- 外汇：Frankfurter（EUR基）

注意：为避免在测试环境硬依赖第三方库，import 放在函数内部；非测试环境调用这些函数时需要安装依赖：
  python3 -m pip install yfinance requests
"""

from __future__ import annotations

from typing import List, Dict, Optional


def fetch_fx_rates_usd(base: str, quote_list: List[str]) -> Dict[str, float]:
    import requests
    # Frankfurter 最新 EUR 基础报价
    r = requests.get("https://api.frankfurter.app/latest", timeout=10)
    r.raise_for_status()
    data = r.json()
    rates = data.get("rates", {})
    rates["EUR"] = 1.0
    # 计算 base→USD、quote→USD 需要的交叉：若 base 不是 USD
    def to_usd(cur: str) -> Optional[float]:
        if cur == "USD":
            return 1.0
        # EUR→USD
        eur_usd = rates.get("USD")
        if eur_usd is None:
            return None
        if cur == "EUR":
            return eur_usd
        # cur→EUR 的逆：EUR→cur = rates[cur]，所以 1 cur = 1/rates[cur] EUR
        cur_per_eur = rates.get(cur)
        if cur_per_eur is None or cur_per_eur == 0:
            return None
        # 1 cur = (1/cur_per_eur) EUR = (1/cur_per_eur)*eur_usd USD
        return (1.0 / cur_per_eur) * eur_usd

    out: Dict[str, float] = {}
    for q in quote_list:
        v = to_usd(q)
        if v is not None:
            out[q] = v
    # 也返回 base 的 USD 价
    base_v = to_usd(base)
    if base_v is not None:
        out[base] = base_v
    return out


def fetch_index_history(symbols: List[str], period: str = "5y") -> Dict[str, List[Dict]]:
    import yfinance as yf
    out: Dict[str, List[Dict]] = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period=period, interval="1d", auto_adjust=False)
            # 仅保留有收盘价的日期
            rows = []
            for ts, row in hist.iterrows():
                close = row.get("Close")
                if close is None:
                    continue
                rows.append({"date": ts.strftime("%Y-%m-%d"), "close": float(close)})
            out[sym] = rows
        except Exception:
            out[sym] = []
    return out


def fetch_fx_timeseries_to_usd(quote_list: List[str], start_date: str, end_date: str) -> Dict[str, Dict[str, float]]:
    """
    返回按日期的货币→USD 汇率字典：{ 'YYYY-MM-DD': { 'JPY': x, 'GBP': y, 'EUR': z, 'USD': 1.0 } }
    说明：Frankfurter 以 EUR 为基准，返回 EUR→C 的汇率；我们需要 C→USD：
      C→USD = (1 / (EUR→C)) * (EUR→USD)
    特殊：C 为 EUR 时，C→USD = EUR→USD；C 为 USD 时，= 1.0。
    """
    import requests
    # 需要的目标货币集合（用于一次拉取所有 quote 的时序）
    quotes = set(quote_list or [])
    quotes.add("USD")
    if "EUR" not in quotes:
        quotes.add("EUR")
    to_param = ",".join(sorted(quotes))
    url = f"https://api.frankfurter.app/{start_date}..{end_date}?to={to_param}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    rates = data.get("rates", {})  # {date: {CUR: rate}}
    out: Dict[str, Dict[str, float]] = {}
    for d, m in rates.items():
        # EUR→USD
        eur_usd = m.get("USD")
        if eur_usd is None:
            continue
        day_map: Dict[str, float] = {"USD": 1.0, "EUR": float(eur_usd)}
        for cur in quotes:
            if cur in ("USD", "EUR"):
                continue
            eur_to_cur = m.get(cur)
            if eur_to_cur is None or eur_to_cur == 0:
                continue
            cur_to_usd = (1.0 / float(eur_to_cur)) * float(eur_usd)
            day_map[cur] = cur_to_usd
        out[d] = day_map
    return out


