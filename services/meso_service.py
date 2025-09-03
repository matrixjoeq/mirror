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
    def refresh_prices_and_scores(self, symbols: Optional[List[str]] = None, period: str = "3y", since: Optional[str] = None, return_mode: str = "price") -> Dict[str, Any]:
        # 仅真实数据，不做样本；调用者需确保网络可用并安装依赖
        syms = symbols or [row["symbol"] for row in INDEX_DEFS]
        from .data_providers.meso_market_provider import (
            fetch_index_history,
            fetch_fx_timeseries_to_usd,
        )

        # 抓取历史收盘价
        use_adjusted = (return_mode == "total")
        hist_map = fetch_index_history(syms, period=period, start=since, adjusted=False, total_return=(return_mode == "total"))

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
        # 前向填充每日汇率，避免非USD币种缺失时错误使用1.0
        all_fx_dates = sorted(fx_ts.keys())
        currencies = set(unique_curs)
        currencies.add("USD")
        ff_fx_ts: Dict[str, Dict[str, float]] = {}
        last_seen: Dict[str, float] = {"USD": 1.0}
        for d in all_fx_dates:
            day_map = fx_ts.get(d, {}) or {}
            # 更新已知汇率
            for c in currencies:
                if c == "USD":
                    last_seen["USD"] = 1.0
                    continue
                v = day_map.get(c)
                if v is not None:
                    last_seen[c] = float(v)
            # 写入前向填充后的映射
            ff_fx_ts[d] = {c: last_seen[c] for c in last_seen if c in currencies and c in last_seen}

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
                day_fx = ff_fx_ts.get(d, {})
                usd_rate = 1.0 if cur == "USD" else day_fx.get(cur)
                # 若当日汇率不可得（含前向填充后仍无），则跳过该日USD换算
                close_usd = (close * usd_rate) if (close is not None and usd_rate is not None) else None
                # total return 路径（若有）
                close_tr = r.get("close_tr")
                close_usd_tr = (close_tr * usd_rate) if (close_tr is not None and usd_rate is not None) else None
                price_rows.append({
                    "symbol": sym,
                    "date": d,
                    "close": close,
                    "close_tr": close_tr,
                    "currency": cur,
                    "close_usd": close_usd,
                    "close_usd_tr": close_usd_tr,
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

    # ------- 管理与设置 -------
    def upsert_tracked_instruments(self, instruments: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not instruments:
            return {"updated": 0}
        updated = self.repo.upsert_index_metadata(instruments)
        return {"updated": updated}

    def list_tracked_instruments(self, only_active: bool = True) -> List[Dict[str, Any]]:
        return self.repo.list_index_metadata(only_active=only_active)

    def set_global_start_date(self, date_str: str) -> Dict[str, Any]:
        self.repo.set_global_start_date(date_str)
        return {"ok": True, "global_start_date": date_str}

    # ------- 基础大类资产强度对比（MVP） -------
    def get_asset_class_rankings(self, asof: Optional[str] = None, top: int = 10, return_mode: str = "price") -> Dict[str, Any]:
        symbols: List[str] = [row.get("symbol") for row in self.repo.list_index_metadata(only_active=True)]
        meta_map: Dict[str, Dict[str, Any]] = {row.get("symbol"): row for row in self.repo.list_index_metadata(only_active=True)}
        rankings: List[Dict[str, Any]] = []
        asof_date = asof or datetime.utcnow().strftime("%Y-%m-%d")

        for sym in symbols:
            prices = self.repo.fetch_prices(sym)
            # 取 close_usd 时间序列
            if return_mode == "total":
                series = [(p["date"], p.get("close_usd_tr")) for p in prices if p.get("close_usd_tr") is not None]
            else:
                series = [(p["date"], p.get("close_usd")) for p in prices if p.get("close_usd") is not None]
            if not series:
                continue
            # 确保按日期排序
            series.sort(key=lambda x: x[0])
            # 定位 asof 索引
            dates = [d for d, _ in series]
            if asof_date not in dates:
                # 找到 <= asof 的最后一个日期
                dates_le = [d for d in dates if d <= asof_date]
                if not dates_le:
                    continue
                use_date = max(dates_le)
            else:
                use_date = asof_date
            idx = dates.index(use_date)
            def window_return(window_days: int) -> Optional[float]:
                if idx - window_days < 0:
                    return None
                v_now = float(series[idx][1])
                v_past = float(series[idx - window_days][1])
                if v_past == 0:
                    return None
                return v_now / v_past - 1.0
            r1 = window_return(21)
            r3 = window_return(63)
            r6 = window_return(126)
            r12 = window_return(252)
            # 降级处理：缺失用可得窗口按权重归一（MVP）
            weights = []
            rets = []
            if r12 is not None:
                weights.append(0.4); rets.append(r12)
            if r6 is not None:
                weights.append(0.3); rets.append(r6)
            if r3 is not None:
                weights.append(0.2); rets.append(r3)
            if r1 is not None:
                weights.append(0.1); rets.append(r1)
            if not weights:
                continue
            total_w = sum(weights)
            composite = sum(w * r for w, r in zip(weights, rets)) / (total_w if total_w else 1.0)
            rankings.append({
                "symbol": sym,
                "asof": use_date,
                "asset_class": meta_map.get(sym, {}).get("asset_class", "unknown"),
                "market": meta_map.get(sym, {}).get("market", ""),
                "composite": composite,
            })

        # 聚合到资产大类：取该类中 composite 的最大值（代表该类最强者）
        class_score: Dict[str, float] = {}
        for row in rankings:
            ac = row.get("asset_class", "unknown")
            score = row.get("composite", 0.0)
            if ac not in class_score or score > class_score[ac]:
                class_score[ac] = score
        ordered = sorted(class_score.items(), key=lambda kv: kv[1], reverse=True)
        result = [{"asset_class": ac, "score": sc} for ac, sc in ordered[:top]]
        return {"asof": asof_date, "rankings": result}

    # ------- 股票：跨市场横向排名（equity.market） -------
    def get_equity_market_rankings(self, asof: Optional[str] = None, top: int = 10, return_mode: str = "price") -> Dict[str, Any]:
        items = self.repo.list_index_metadata(only_active=True)
        # 仅 equity
        symbols = [row.get("symbol") for row in items if str(row.get("asset_class", "")).lower() == "equity"]
        meta_map: Dict[str, Dict[str, Any]] = {row.get("symbol"): row for row in items}
        asof_date = asof or datetime.utcnow().strftime("%Y-%m-%d")

        # 计算每个 symbol 的 composite
        symbol_scores: Dict[str, float] = {}
        for sym in symbols:
            prices = self.repo.fetch_prices(sym)
            series = (
                [(p["date"], p.get("close_usd_tr")) for p in prices if p.get("close_usd_tr") is not None]
                if return_mode == "total"
                else [(p["date"], p.get("close_usd")) for p in prices if p.get("close_usd") is not None]
            )
            if not series:
                continue
            series.sort(key=lambda x: x[0])
            dates = [d for d, _ in series]
            use_date = asof_date if asof_date in dates else (max([d for d in dates if d <= asof_date]) if any(d <= asof_date for d in dates) else None)
            if not use_date:
                continue
            idx = dates.index(use_date)
            def window_return(window_days: int) -> Optional[float]:
                if idx - window_days < 0:
                    return None
                v_now = float(series[idx][1])
                v_past = float(series[idx - window_days][1])
                if v_past == 0:
                    return None
                return v_now / v_past - 1.0
            r1 = window_return(21)
            r3 = window_return(63)
            r6 = window_return(126)
            r12 = window_return(252)
            weights, rets = [], []
            if r12 is not None:
                weights.append(0.4); rets.append(r12)
            if r6 is not None:
                weights.append(0.3); rets.append(r6)
            if r3 is not None:
                weights.append(0.2); rets.append(r3)
            if r1 is not None:
                weights.append(0.1); rets.append(r1)
            if not weights:
                continue
            total_w = sum(weights)
            composite = sum(w * r for w, r in zip(weights, rets)) / (total_w if total_w else 1.0)
            symbol_scores[sym] = composite

        # 聚合到 market：取该市场中 composite 的最大值
        market_score: Dict[str, float] = {}
        for sym, comp in symbol_scores.items():
            mkt = str(meta_map.get(sym, {}).get("market", "")).upper() or "UNKNOWN"
            if mkt not in market_score or comp > market_score[mkt]:
                market_score[mkt] = comp
        ordered = sorted(market_score.items(), key=lambda kv: kv[1], reverse=True)
        result = [{"market": mk, "score": sc} for mk, sc in ordered[:top]]
        return {"asof": asof_date, "rankings": result}

    # ------- 市场内：按类别横向排名（equity.category within market） -------
    def get_equity_category_rankings(self, market: str, asof: Optional[str] = None, top: int = 10, return_mode: str = "price") -> Dict[str, Any]:
        items = self.repo.list_index_metadata(only_active=True)
        market_u = (market or "").upper()
        # 仅 equity 且指定市场
        symbols = [row.get("symbol") for row in items if str(row.get("asset_class", "")).lower() == "equity" and str(row.get("market", "")).upper() == market_u]
        meta_map: Dict[str, Dict[str, Any]] = {row.get("symbol"): row for row in items}
        asof_date = asof or datetime.utcnow().strftime("%Y-%m-%d")
        symbol_scores: Dict[str, float] = {}
        for sym in symbols:
            prices = self.repo.fetch_prices(sym)
            series = (
                [(p["date"], p.get("close_usd_tr")) for p in prices if p.get("close_usd_tr") is not None]
                if return_mode == "total"
                else [(p["date"], p.get("close_usd")) for p in prices if p.get("close_usd") is not None]
            )
            if not series:
                continue
            series.sort(key=lambda x: x[0])
            dates = [d for d, _ in series]
            use_date = asof_date if asof_date in dates else (max([d for d in dates if d <= asof_date]) if any(d <= asof_date for d in dates) else None)
            if not use_date:
                continue
            idx = dates.index(use_date)
            def window_return(window_days: int) -> Optional[float]:
                if idx - window_days < 0:
                    return None
                v_now = float(series[idx][1])
                v_past = float(series[idx - window_days][1])
                if v_past == 0:
                    return None
                return v_now / v_past - 1.0
            r1 = window_return(21)
            r3 = window_return(63)
            r6 = window_return(126)
            r12 = window_return(252)
            weights, rets = [], []
            if r12 is not None:
                weights.append(0.4); rets.append(r12)
            if r6 is not None:
                weights.append(0.3); rets.append(r6)
            if r3 is not None:
                weights.append(0.2); rets.append(r3)
            if r1 is not None:
                weights.append(0.1); rets.append(r1)
            if not weights:
                continue
            total_w = sum(weights)
            composite = sum(w * r for w, r in zip(weights, rets)) / (total_w if total_w else 1.0)
            symbol_scores[sym] = composite

        # 聚合到类别：取该类别中 composite 的最大值
        cat_score: Dict[str, float] = {}
        for sym, comp in symbol_scores.items():
            cat = str(meta_map.get(sym, {}).get("category", "")).lower() or "unknown"
            if cat not in cat_score or comp > cat_score[cat]:
                cat_score[cat] = comp
        ordered = sorted(cat_score.items(), key=lambda kv: kv[1], reverse=True)
        result = [{"category": cat, "score": sc} for cat, sc in ordered[:top]]
        return {"market": market_u, "asof": asof_date, "rankings": result}


