#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中观观察体系 - 服务层（全球股市趋势对比）

说明：
- 仅提供最小可用接口；真实数据来源需外部 provider（后续接入）。
- 非测试环境不做任何样本兜底；测试环境可选保留样本（当前先不实现样本）。
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import time

from .meso_repository import MesoRepository
from .meso_config import INDEX_DEFS, index_currency_map


class MesoService:
    def __init__(self):
        self.repo = MesoRepository()

    def list_indexes(self) -> List[Dict[str, Any]]:
        # 最小占位，后续由配置/provider 返回可用清单
        return [
            {"symbol": "^GSPC", "name": "S&P 500", "region": "Americas", "currency": "USD"},
            {"symbol": "^NDX", "name": "Nasdaq 100", "region": "Americas", "currency": "USD"},
            {"symbol": "^STOXX50E", "name": "Euro STOXX 50", "region": "EMEA", "currency": "EUR"},
            {"symbol": "^N225", "name": "Nikkei 225", "region": "APAC", "currency": "JPY"},
            {"symbol": "^HSI", "name": "Hang Seng", "region": "APAC", "currency": "HKD"},
        ]

    def get_trend_series(self, symbol: str, window: str = "3y", currency: str = "USD") -> Dict[str, Any]:
        # 读取已存储的分数与价格（真实序列应由抓取与计算流程提前写入 repo）
        series_scores = self.repo.fetch_scores(symbol)
        series_prices = self.repo.fetch_prices(symbol)
        return {
            "symbol": symbol,
            "window": window,
            "currency": currency,
            "scores": series_scores,
            "prices": series_prices,
        }

    def get_compare_series(self, symbols: List[str], window: str = "3y", currency: str = "USD") -> Dict[str, Any]:
        if not symbols or len(symbols) > 10:
            raise ValueError("symbols must be 1..10")
        data: Dict[str, List[Dict[str, Any]]] = {}
        for sym in symbols:
            data[sym] = self.repo.fetch_scores(sym)
        return {"symbols": symbols, "window": window, "currency": currency, "series": data}

    # ---- 真实数据刷新 ----
    def refresh_prices_and_scores(self, symbols: Optional[List[str]] = None, period: str = "3y") -> Dict[str, Any]:
        # 仅真实数据，不做样本；调用者需确保网络可用并安装依赖
        syms = symbols or [row["symbol"] for row in INDEX_DEFS]
        from .data_providers.meso_market_provider import (
            fetch_index_history,
            fetch_fx_timeseries_to_usd,
        )

        # 抓取历史收盘价
        hist_map = fetch_index_history(syms, period=period)

        # 计算增量边界：按各 symbol 最新已存日期+1 作为起始
        cur_map = index_currency_map()
        min_start: Optional[str] = None
        for sym in syms:
            last = self.repo.get_latest_price_date(sym)
            if last is None:
                # 无数据，则允许整个 period
                continue
            # 下一天（简化：不加一天，直接交由去重 INSERT OR REPLACE，避免日期运算依赖）
            if min_start is None or last < min_start:
                min_start = last

        # 推断 timeseries 的起止（若无本地数据，则用历史里最早/最晚日期）
        all_dates = [r["date"] for rows in hist_map.values() for r in rows]
        if not all_dates:
            return {"refreshed": True, "symbols": syms, "prices": 0, "scores": 0}
        start_date = min(all_dates) if min_start is None else min(all_dates)
        end_date = max(all_dates)

        # 拉取历史当日汇率时序并换算到 USD
        unique_curs = sorted(set(cur_map.get(s, "USD") for s in syms))
        fx_ts = fetch_fx_timeseries_to_usd(unique_curs, start_date, end_date)  # {date: {CUR: USD_rate}}

        # 写入价格表（含“当日汇率”换算到 USD），仅增量（大于已存的最后日期）
        price_rows: List[Dict[str, Any]] = []
        for sym, rows in hist_map.items():
            cur = cur_map.get(sym, "USD")
            last_date = self.repo.get_latest_price_date(sym)
            for r in rows:
                d = r["date"]
                if last_date and d <= last_date:
                    continue
                close = float(r["close"]) if r.get("close") is not None else None
                day_fx = fx_ts.get(d, {})
                usd_rate = day_fx.get(cur, 1.0)
                close_usd = (close * usd_rate) if close is not None else None
                price_rows.append({
                    "symbol": sym,
                    "date": d,
                    "close": close,
                    "currency": cur,
                    "close_usd": close_usd,
                })
        if price_rows:
            self.repo.upsert_index_prices(price_rows)

        # 计算一个最简趋势分（示意：最近63日收益归一到 [0,100]），仅增量
        score_rows: List[Dict[str, Any]] = []
        for sym in syms:
            series = self.repo.fetch_prices(sym)
            closes = [(p["date"], p["close_usd"]) for p in series if p.get("close_usd") is not None]
            last_score_date = self.repo.get_latest_score_date(sym)
            # 按日期累积，窗口内收益
            for i in range(len(closes)):
                if i < 62:
                    continue
                d, v = closes[i]
                if last_score_date and d <= last_score_date:
                    continue
                v0 = closes[i - 62][1]
                if v0 is None or v is None or v0 == 0:
                    continue
                ret = (float(v) / float(v0) - 1.0)
                # 简单映射到分数区间 [0,100]（-20%→0，+20%→100，超出截断）
                raw = (ret + 0.2) / 0.4
                score = max(0.0, min(1.0, raw)) * 100.0
                score_rows.append({
                    "symbol": sym,
                    "date": d,
                    "score": score,
                    "components_json": None,
                })
        if score_rows:
            self.repo.upsert_trend_scores(score_rows)

        return {"refreshed": True, "symbols": syms, "prices": len(price_rows), "scores": len(score_rows)}


