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
        # 提前获取 instrument_type map
        meta = {row.get("symbol"): str(row.get("instrument_type") or "").upper() for row in self.repo.list_index_metadata(only_active=True)}
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
                adj_factor = r.get("adj_factor")
                price_rows.append({
                    "symbol": sym,
                    "date": d,
                    "close": close,
                    "close_tr": close_tr,
                    "currency": cur,
                    "close_usd": close_usd,
                    "close_usd_tr": close_usd_tr,
                    "adj_factor": adj_factor,
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

        # 对于 ETF/股票：全量计算复权价格（使用 adj_factor）并写回
        adj_rows: List[Dict[str, Any]] = []
        for sym in syms:
            if meta.get(sym) not in ("ETF","STOCK"):
                continue
            rows = self.repo.fetch_prices(sym)
            # 用最近一日的 adj_factor 累积生成前/后复权（简化：此处用当日adj_factor推导 TR，如果需要精确分红拆分可扩展）
            # 这里实现一个基础版：close_tr = close * adj_factor；close_usd_tr = close_usd * adj_factor
            for p in rows:
                af = p.get("adj_factor")
                if af is None or p.get("close") is None:
                    continue
                try:
                    tr = float(p["close"]) * float(af)
                    tr_usd = float(p["close_usd"]) * float(af) if p.get("close_usd") is not None else None
                    adj_rows.append({"date": p["date"], "close_tr": tr, "close_usd_tr": tr_usd})
                except Exception:
                    continue
            if adj_rows:
                self.repo.update_adjusted_prices(sym, adj_rows)
                adj_rows.clear()

        return {"refreshed": True, "symbols": syms, "prices": len(price_rows), "scores": len(score_rows)}

    # ------- 管理与设置 -------
    # 旧方法名重复，移除

    def list_tracked_instruments(self, only_active: bool = True) -> List[Dict[str, Any]]:
        return self.repo.list_index_metadata(only_active=only_active)

    def set_global_start_date(self, date_str: str) -> Dict[str, Any]:
        self.repo.set_global_start_date(date_str)
        return {"ok": True, "global_start_date": date_str}

    def upsert_tracked_instruments(self, instruments: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not instruments:
            return {"updated": 0}
        # 规范化大小写与缺省
        normed: List[Dict[str, Any]] = []
        for r in instruments:
            r = dict(r)
            if r.get("market"):
                r["market"] = str(r["market"]).upper()
            if r.get("instrument_type"):
                r["instrument_type"] = str(r["instrument_type"]).upper()
            if r.get("provider"):
                r["provider"] = str(r["provider"]).upper()
            normed.append(r)
        updated = self.repo.upsert_index_metadata(normed)
        return {"updated": updated}

    # ------- 基础大类资产强度对比（MVP） -------
    def get_asset_class_rankings(self, asof: Optional[str] = None, top: int = 10, return_mode: str = "price") -> Dict[str, Any]:
        """
        统一强制口径：
        - 统一货币：USD（price: close_usd；total: close_usd_tr）
        - 统一时间尺度：从全局起始日期至 asof 的“各市场共同开市日交集”
        - 统一价格指标：return_mode=price|total（二选一）
        """
        rm = (return_mode or "price").lower()
        if rm not in ("price", "total"):
            rm = "price"

        items = self.repo.list_index_metadata(only_active=True)
        symbols: List[str] = [row.get("symbol") for row in items]
        meta_map: Dict[str, Dict[str, Any]] = {row.get("symbol"): row for row in items}

        # 确定全局起始日期与参与市场集合
        global_start = self.repo.get_global_start_date() or "2000-01-01"
        markets: List[str] = sorted({str(row.get("market", "")).upper() for row in items if row.get("market")})
        # 共同开市日（以有有效USD价格为准）
        common_dates_all = self.repo.get_common_open_dates(markets, global_start) if markets else []
        asof_date = asof or (common_dates_all[-1] if common_dates_all else datetime.utcnow().strftime("%Y-%m-%d"))
        # 取 <= asof 的共同日期
        common_dates = [d for d in common_dates_all if d <= asof_date]
        if not common_dates:
            return {"asof": asof_date, "rankings": []}

        # 用共同日期过滤每个标的的USD序列
        rankings: List[Dict[str, Any]] = []
        use_date = common_dates[-1]

        for sym in symbols:
            prices = self.repo.fetch_prices(sym)
            if rm == "total":
                series = [(p["date"], p.get("close_usd_tr")) for p in prices if (p["date"] in common_dates and p.get("close_usd_tr") is not None)]
            else:
                series = [(p["date"], p.get("close_usd")) for p in prices if (p["date"] in common_dates and p.get("close_usd") is not None)]
            if not series:
                continue
            series.sort(key=lambda x: x[0])
            dates = [d for d, _ in series]
            if use_date not in dates:
                # 若该标的在共同日期末日仍缺数据，则跳过
                continue
            idx = dates.index(use_date)

            def window_return_by_count(window_days: int) -> Optional[float]:
                if idx - window_days < 0:
                    return None
                v_now = float(series[idx][1])
                v_past = float(series[idx - window_days][1])
                if v_past == 0:
                    return None
                return v_now / v_past - 1.0

            r1 = window_return_by_count(21)
            r3 = window_return_by_count(63)
            r6 = window_return_by_count(126)
            r12 = window_return_by_count(252)

            weights: List[float] = []
            rets: List[float] = []
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

        # 聚合到资产大类（以类别内最强者代表该类打分）
        class_score: Dict[str, float] = {}
        for row in rankings:
            ac = row.get("asset_class", "unknown")
            score = row.get("composite", 0.0)
            if ac not in class_score or score > class_score[ac]:
                class_score[ac] = score
        ordered = sorted(class_score.items(), key=lambda kv: kv[1], reverse=True)
        if top == 1 and ordered:
            result = [{"asset_class": ordered[0][0], "score": ordered[0][1]}]
        else:
            result = [{"asset_class": ac, "score": sc} for ac, sc in ordered[:top]]
        return {"asof": use_date, "return_mode": rm, "rankings": result}

    # ------- 观察对象总览（按层级聚合） -------
    def get_instruments_overview(self) -> Dict[str, Any]:
        items = self.repo.list_index_metadata(only_active=False)
        out: Dict[str, Any] = {"by_asset_class": {}, "by_market": {}, "by_category": {}, "all": []}
        for row in items:
            sym = row.get("symbol")
            rng = self.repo.get_price_date_range(sym)
            rec = {
                "symbol": sym,
                "name": row.get("name"),
                "currency": row.get("currency"),
                "provider": row.get("provider"),
                "market": row.get("market"),
                "asset_class": row.get("asset_class"),
                "category": row.get("category"),
                "subcategory": row.get("subcategory"),
                "min_date": rng.get("min_date"),
                "max_date": rng.get("max_date"),
                "has_usd": rng.get("has_usd"),
                "has_tr": rng.get("has_tr"),
                "has_usd_tr": rng.get("has_usd_tr"),
                "is_active": bool(row.get("is_active", 1)),
            }
            out["all"].append(rec)
            ac = str(row.get("asset_class") or "unknown")
            mk = str(row.get("market") or "unknown")
            cat = str(row.get("category") or "unknown")
            out["by_asset_class"].setdefault(ac, []).append(rec)
            out["by_market"].setdefault(mk, []).append(rec)
            out["by_category"].setdefault(cat, []).append(rec)
        return out

    # ------- 股票：跨市场横向排名（equity.market） -------
    def get_equity_market_rankings(self, asof: Optional[str] = None, top: int = 10, return_mode: str = "price") -> Dict[str, Any]:
        """
        跨市场（equity）横向排名：强制 USD + 各市场共同开市日交集 + 统一价格指标。
        """
        rm = (return_mode or "price").lower()
        if rm not in ("price", "total"):
            rm = "price"

        items = self.repo.list_index_metadata(only_active=True)
        eq_items = [row for row in items if str(row.get("asset_class", "")).lower() == "equity"]
        symbols = [row.get("symbol") for row in eq_items]
        meta_map: Dict[str, Dict[str, Any]] = {row.get("symbol"): row for row in eq_items}

        # 市场集合与共同开市日（跨市场）
        markets: List[str] = sorted({str(row.get("market", "")).upper() for row in eq_items if row.get("market")})
        global_start = self.repo.get_global_start_date() or "2000-01-01"
        common_dates_all = self.repo.get_common_open_dates(markets, global_start) if markets else []
        asof_date = asof or (common_dates_all[-1] if common_dates_all else datetime.utcnow().strftime("%Y-%m-%d"))
        common_dates = [d for d in common_dates_all if d <= asof_date]
        if not common_dates:
            return {"asof": asof_date, "return_mode": rm, "rankings": []}
        use_date = common_dates[-1]

        # 计算每个 symbol 的 composite（基于 USD 或 USD-TR）
        symbol_scores: Dict[str, float] = {}
        for sym in symbols:
            prices = self.repo.fetch_prices(sym)
            series = (
                [(p["date"], p.get("close_usd_tr")) for p in prices if (p["date"] in common_dates and p.get("close_usd_tr") is not None)]
                if rm == "total"
                else [(p["date"], p.get("close_usd")) for p in prices if (p["date"] in common_dates and p.get("close_usd") is not None)]
            )
            if not series:
                continue
            series.sort(key=lambda x: x[0])
            dates = [d for d, _ in series]
            if use_date not in dates:
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

        market_score: Dict[str, float] = {}
        for sym, comp in symbol_scores.items():
            mkt = str(meta_map.get(sym, {}).get("market", "")).upper() or "UNKNOWN"
            if mkt not in market_score or comp > market_score[mkt]:
                market_score[mkt] = comp
        ordered = sorted(market_score.items(), key=lambda kv: kv[1], reverse=True)
        result = [{"market": mk, "score": sc} for mk, sc in ordered[:top]]
        return {"asof": use_date, "return_mode": rm, "rankings": result}

    # ------- 市场内：按类别横向排名（equity.category within market） -------
    def get_equity_category_rankings(self, market: str, asof: Optional[str] = None, top: int = 10, return_mode: str = "price") -> Dict[str, Any]:
        items = self.repo.list_index_metadata(only_active=True)
        market_u = (market or "").upper()
        # 仅 equity 且指定市场
        symbols = [row.get("symbol") for row in items if str(row.get("asset_class", "")).lower() == "equity" and str(row.get("market", "")).upper() == market_u]
        meta_map: Dict[str, Dict[str, Any]] = {row.get("symbol"): row for row in items}
        # 本市场共同开市日（使用本币价格，不要求 USD）
        global_start = self.repo.get_global_start_date() or "2000-01-01"
        common_dates_all = self.repo.get_common_open_dates([market_u], global_start)
        asof_date = asof or (common_dates_all[-1] if common_dates_all else datetime.utcnow().strftime("%Y-%m-%d"))
        common_dates = [d for d in common_dates_all if d <= asof_date]
        if not common_dates:
            return {"market": market_u, "asof": asof_date, "return_mode": (return_mode or "price"), "rankings": []}
        use_date = common_dates[-1]
        symbol_scores: Dict[str, float] = {}
        for sym in symbols:
            prices = self.repo.fetch_prices(sym)
            # 本市场内部用本币价格序列：price→close，total→close_tr
            series = (
                [(p["date"], p.get("close_tr")) for p in prices if (p["date"] in common_dates and p.get("close_tr") is not None)]
                if (return_mode or "price").lower() == "total"
                else [(p["date"], p.get("close")) for p in prices if (p["date"] in common_dates and p.get("close") is not None)]
            )
            if not series:
                continue
            series.sort(key=lambda x: x[0])
            dates = [d for d, _ in series]
            if use_date not in dates:
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


