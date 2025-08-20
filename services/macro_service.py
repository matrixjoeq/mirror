#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观观察体系 - 服务层（MVP脚手架）

说明：
- 提供对外 API 所需的最小可用接口，返回结构化结果，便于前端/模板渲染。
- 真实数据接入通过 MacroRepository + Provider 适配层逐步完善。
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List, Tuple

from .database_service import DatabaseService
from .macro_repository import MacroRepository
from .macro_config import ECONOMIES, COMMODITIES, INDICATORS, INDICATOR_WEIGHTS
from .data_providers.market_provider import fetch_commodities_latest, fetch_fx_latest
from .data_providers.worldbank_provider import fetch_macro_latest as wb_fetch_macro_latest
from datetime import datetime, timezone
import time
import copy

# 简单的进程内快照缓存（TTL）
_SNAPSHOT_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_SNAPSHOT_TTL_SECONDS: int = 300  # 5 分钟
_CACHE_VERSION: int = 0

def _make_cache_key(view: str, date: Optional[str], window: Optional[str]) -> str:
    return f"v{_CACHE_VERSION}|{(view or 'value').lower()}|{date or ''}|{window or ''}"


class MacroService:
    """宏观观察服务（MVP）"""

    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        self.repo = MacroRepository(db_service)

    # --------- 对外接口（API/页面使用） ---------
    def get_snapshot(self, view: str = "value", date: Optional[str] = None, window: Optional[str] = None, nocache: bool = False) -> Dict[str, Any]:
        """返回热力/排行快照（纯真实数据，无样例/兜底）。"""
        # 缓存命中（仅对未过滤的基础快照做缓存；后置过滤在路由层处理）
        cache_key = _make_cache_key(view, date, window)
        now = time.time()
        if not nocache:
            entry = _SNAPSHOT_CACHE.get(cache_key)
            if entry and entry[0] > now:
                # 返回深拷贝，避免被路由过滤修改污染缓存
                return copy.deepcopy(entry[1])
        economies = ECONOMIES
        commodities = COMMODITIES
        # 计算最新值
        indicators_directions: List[Tuple[str, int]] = [(k, d) for k, (d, _w) in INDICATORS.items()]
        latest_values: Dict[str, Dict[str, float]] = {eco: {} for eco in economies}
        for ind, _dir in indicators_directions:
            latest_map = self.repo.fetch_latest_by_indicator(ind)
            for eco in economies:
                if eco in latest_map:
                    latest_values[eco][ind] = latest_map[eco]

        # 评分方法：value=min-max; zscore=按z后再min-max到[0,1]; percentile=以各经济体分位映射[0,1]
        method = (view or "value").lower()
        indicator_scores: Dict[str, Dict[str, float]] = {eco: {} for eco in economies}
        for ind, direction in indicators_directions:
            vals: List[float] = [latest_values[eco].get(ind) for eco in economies if ind in latest_values[eco]]
            if not vals:
                continue
            if method == "trend":
                # 用最近两期差分做方向一致化后映射：正向指标用 (latest-prev)，负向指标用 (prev-latest)
                two_map = self.repo.fetch_latest_two_by_indicator(ind)
                diffs: Dict[str, float] = {}
                for eco in economies:
                    latest_prev = two_map.get(eco)
                    if not latest_prev:
                        continue
                    latest_v, prev_v = latest_prev
                    if latest_v is None or prev_v is None:
                        continue
                    raw_diff = latest_v - prev_v
                    aligned_diff = raw_diff if direction >= 0 else (-raw_diff)
                    diffs[eco] = aligned_diff
                if not diffs:
                    continue
                dmin = min(diffs.values())
                dmax = max(diffs.values())
                dspan = dmax - dmin
                for eco, dv in diffs.items():
                    norm = 0.5 if dspan == 0 else (dv - dmin) / dspan
                    indicator_scores[eco][ind] = max(0.0, min(1.0, norm))
                continue
            if method == "zscore":
                mean_value = sum(vals) / len(vals)
                variance = sum((v - mean_value) ** 2 for v in vals) / len(vals)
                std_dev = variance ** 0.5
                zs = [0.0 if std_dev == 0 else (v - mean_value) / std_dev for v in vals]
                z_min, z_max = min(zs), max(zs)
                z_span = z_max - z_min
            elif method == "percentile":
                sorted_values = sorted(vals)
            else:
                v_min, v_max = min(vals), max(vals)
                v_span = v_max - v_min

            for eco in economies:
                v = latest_values[eco].get(ind)
                if v is None:
                    continue
                if method == "zscore":
                    if std_dev == 0 or z_span == 0:
                        norm = 0.5
                    else:
                        z = (v - mean_value) / std_dev
                        norm = (z - z_min) / z_span
                elif method == "percentile":
                    try:
                        idx = sorted_values.index(v)
                    except ValueError:
                        idx = 0
                    n = len(sorted_values)
                    norm = (idx / (n - 1)) if n > 1 else 0.5
                else:
                    if v_span == 0:
                        norm = 0.5
                    else:
                        norm = (v - v_min) / v_span
                aligned = norm if direction >= 0 else (1.0 - norm)
                indicator_scores[eco][ind] = max(0.0, min(1.0, aligned))

        matrix: Dict[str, Dict[str, Any]] = {}
        ranking: List[Dict[str, Any]] = []
        for eco in economies:
            # 加权均值（默认权重 1.0）
            comps = []
            weights = []
            for ind, score01 in indicator_scores[eco].items():
                comps.append(score01)
                weights.append(INDICATOR_WEIGHTS.get(ind, 1.0))
            comp = (sum(c*w for c, w in zip(comps, weights)) / (sum(weights) or 1.0) * 100.0) if comps else 0.0
            matrix[eco] = {
                "composite": round(comp, 1),
                "by_indicator": {ind: round(val * 100.0, 1) for ind, val in indicator_scores[eco].items()},
            }
            ranking.append({"economy": eco, "score": round(comp, 1)})
        ranking.sort(key=lambda x: x["score"], reverse=True)
        payload = {
            "as_of": date or "",
            "view": view,
            "window": window or "3y",
            "economies": economies,
            "commodities": commodities,
            "matrix": matrix,
            "ranking": ranking,
        }
        # 写缓存
        _SNAPSHOT_CACHE[cache_key] = (now + _SNAPSHOT_TTL_SECONDS, copy.deepcopy(payload))
        return payload

    def get_country(self, economy: str, window: str = "3y") -> Dict[str, Any]:
        """返回单个经济体关键指标时间序列与综合分（MVP 实装：回读已种子数据）。"""
        eco = economy.upper()
        series = self.repo.fetch_macro_series_by_economy(eco)
        composite: List[Dict[str, Any]] = []
        # MVP: 若存在任一指标序列，则给出单点 100 分，否则 0 分
        composite.append({"date": "latest", "value": 100.0 if series else 0.0})
        return {
            "economy": eco,
            "window": window,
            "series": series,
            "composite_score": composite,
            "components": {},
        }

    def get_score(self, entity_type: str, entity_id: str, view: str = "trend") -> Dict[str, Any]:
        """返回指定实体（macro/commodity/index/bond/etf）的评分（MVP：固定占位分）。"""
        base = 60.0 if entity_type in ("commodity", "macro") else 50.0
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "view": view,
            "score": base,
            "components": {},
        }

    # ----------------------
    # 内部：最小样本数据
    # ----------------------
    def _seed_minimal_sample(self) -> None:
        """向数据库写入最小样本数据，支撑页面/接口。
        仅在库内无任何数据时执行，幂等不重复插入。
        """
        sample = [
            {"economy": "US", "indicator": "cpi_yoy", "date": "2024-12-01", "value": 3.4, "provider": "sample", "revised_at": None},
            {"economy": "US", "indicator": "unemployment", "date": "2024-12-01", "value": 3.9, "provider": "sample", "revised_at": None},
            {"economy": "DE", "indicator": "cpi_yoy", "date": "2024-12-01", "value": 3.2, "provider": "sample", "revised_at": None},
            {"economy": "JP", "indicator": "cpi_yoy", "date": "2024-12-01", "value": 2.7, "provider": "sample", "revised_at": None},
        ]
        self.repo.bulk_upsert_macro_series(sample)
        # commodity/fx 少量占位
        self.repo.bulk_upsert_commodity_series([
            {"commodity": "brent", "date": "2024-12-01", "value": 78.2, "currency": "USD", "provider": "sample"},
            {"commodity": "gold", "date": "2024-12-01", "value": 2100.0, "currency": "USD", "provider": "sample"},
        ])
        self.repo.bulk_upsert_fx_series([
            {"pair": "EURUSD", "date": "2024-12-01", "price": 1.08},
            {"pair": "USDJPY", "date": "2024-12-01", "price": 150.0},
        ])

    # 对外：刷新（仅尝试真实 Provider 拉取，不做样例兜底）
    def refresh_all(self) -> Dict[str, Any]:
        # 使用 Provider 获取最新市场数据；失败时不落任何数据
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            com_rows = fetch_commodities_latest()
            if com_rows:
                self.repo.bulk_upsert_commodity_series(com_rows)
                self.repo.record_refresh("commodity", ts, len(com_rows))
        except (RuntimeError, ValueError):
            pass
        try:
            fx_rows = fetch_fx_latest()
            if fx_rows:
                self.repo.bulk_upsert_fx_series(fx_rows)
                self.repo.record_refresh("fx", ts, len(fx_rows))
        except (RuntimeError, ValueError):
            pass
        # WorldBank 宏观指标最新数据（网络可用时）
        try:
            from .macro_config import ECONOMIES as _ECOS
            indicators = [name for name in INDICATORS.keys() if name in ("cpi_yoy", "unemployment", "gdp_yoy")]
            wb_rows = wb_fetch_macro_latest(_ECOS, indicators)
            if wb_rows:
                self.repo.bulk_upsert_macro_series(wb_rows)
                self.repo.record_refresh("worldbank", ts, len(wb_rows))
        except (RuntimeError, ValueError):
            pass
        # 刷新后失效缓存（版本+清空）
        global _CACHE_VERSION
        _CACHE_VERSION += 1
        _SNAPSHOT_CACHE.clear()
        return {"refreshed": True, "message": "Refresh completed.", "cache_invalidated": True}


