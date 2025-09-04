#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观观察体系 - 仓储层（MVP脚手架）

说明：
- 负责读写宏观/商品/汇率等序列数据和评分结果。
- 现阶段只创建表结构（幂等），便于后续接入 Provider。
"""

from __future__ import annotations

from typing import Any, Optional

from .database_service import DatabaseService
from config import Config


class MacroRepository:
    def __init__(self, db_service: DatabaseService | None = None):
        # 使用独立的宏观数据库，保证与交易数据库物理隔离
        try:
            from flask import current_app  # 延迟导入避免循环依赖
            macro_db_path = current_app.config.get('MACRO_DB_PATH', Config.MACRO_DB_PATH)
        except Exception:
            macro_db_path = Config.MACRO_DB_PATH
        # 内存库使用独立共享URI，避免与交易库混淆
        if isinstance(macro_db_path, str) and macro_db_path.strip() == ':memory:':
            macro_db_path = 'file:macro_memdb?mode=memory&cache=shared'
        self.db = db_service or DatabaseService(macro_db_path, create_trading_schema=False)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            # 清理：宏观库不应存在交易表，若存在则删除
            try:
                for t in ('strategies','strategy_tags','strategy_tag_relations','trades','trade_details','trade_modifications'):
                    cur.execute(f"DROP TABLE IF EXISTS {t}")
            except Exception:
                pass
            # 表结构与计划文档一致（精简版，MVP可用）
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS macro_series (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    economy TEXT NOT NULL,
                    indicator TEXT NOT NULL,
                    date TEXT NOT NULL,
                    value REAL,
                    provider TEXT,
                    revised_at TEXT,
                    UNIQUE(economy, indicator, date)
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS commodity_series (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    commodity TEXT NOT NULL,
                    date TEXT NOT NULL,
                    value REAL,
                    currency TEXT,
                    provider TEXT,
                    UNIQUE(commodity, date)
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS fx_series (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair TEXT NOT NULL,
                    date TEXT NOT NULL,
                    price REAL,
                    UNIQUE(pair, date)
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    view TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    score REAL,
                    components_json TEXT,
                    UNIQUE(view, entity_type, entity_id, date)
                )
                """
            )

            # 刷新元信息
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS refresh_meta (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    refreshed_at TEXT NOT NULL,
                    rows INTEGER DEFAULT 0
                )
                """
            )

            conn.commit()


    # ----------------------
    # 数据写入（Upsert/批量）
    # ----------------------
    def bulk_upsert_macro_series(self, records: list[dict[str, Any]]) -> int:
        """批量写入/更新 macro_series。

        记录字段：economy, indicator, date, value, provider, revised_at
        返回成功写入的行数。
        """
        if not records:
            return 0
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.executemany(
                (
                    "INSERT OR REPLACE INTO macro_series (economy, indicator, date, value, provider, revised_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)"
                ),
                [
                    (
                        r.get("economy"),
                        r.get("indicator"),
                        r.get("date"),
                        float(r.get("value")) if r.get("value") is not None else None,
                        r.get("provider"),
                        r.get("revised_at"),
                    )
                    for r in records
                ],
            )
            conn.commit()
            return cur.rowcount or 0

    def bulk_upsert_commodity_series(self, records: list[dict[str, Any]]) -> int:
        """批量写入/更新 commodity_series。字段：commodity, date, value, currency, provider"""
        if not records:
            return 0
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.executemany(
                (
                    "INSERT OR REPLACE INTO commodity_series (commodity, date, value, currency, provider) "
                    "VALUES (?, ?, ?, ?, ?)"
                ),
                [
                    (
                        r.get("commodity"),
                        r.get("date"),
                        float(r.get("value")) if r.get("value") is not None else None,
                        r.get("currency"),
                        r.get("provider"),
                    )
                    for r in records
                ],
            )
            conn.commit()
            return cur.rowcount or 0

    def bulk_upsert_fx_series(self, records: list[dict[str, Any]]) -> int:
        """批量写入/更新 fx_series。字段：pair, date, price"""
        if not records:
            return 0
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.executemany(
                "INSERT OR REPLACE INTO fx_series (pair, date, price) VALUES (?, ?, ?)",
                [
                    (
                        r.get("pair"),
                        r.get("date"),
                        float(r.get("price")) if r.get("price") is not None else None,
                    )
                    for r in records
                ],
            )
            conn.commit()
            return cur.rowcount or 0

    # ----------------------
    # 数据读取
    # ----------------------
    def fetch_macro_series_by_economy(self, economy: str) -> dict[str, list[dict[str, Any]]]:
        """按经济体读取时间序列，返回 {indicator: [{date, value}...]} 结构。"""
        result: dict[str, list[dict[str, Any]]] = {}
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT indicator, date, value FROM macro_series WHERE economy = ? ORDER BY indicator, date",
                (economy.upper(),),
            )
            rows = cur.fetchall()
        for row in rows:
            indicator = row[0]
            result.setdefault(indicator, []).append({"date": row[1], "value": row[2]})
        return result

    def fetch_latest_by_indicator(self, indicator: str) -> dict[str, float]:
        """读取某指标各经济体的最近值，返回 {economy: value}。
        若某经济体存在多期，取最新日期。"""
        # value 允许为 None，在过滤时剔除
        latest: dict[str, tuple[str, Optional[float]]] = {}
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT economy, date, value FROM macro_series WHERE indicator = ? ORDER BY economy, date",
                (indicator,),
            )
            for eco, d, v in cur.fetchall():
                # 逐行覆盖，ORDER BY 确保同一 economy 下最后一条为最新日期（字典序日期格式 YYYY-MM-DD）
                latest[str(eco)] = (str(d), float(v) if v is not None else None)
        return {eco: val for eco, (_, val) in latest.items() if val is not None}

    def fetch_latest_two_by_indicator(self, indicator: str) -> dict[str, tuple[Optional[float], Optional[float]]]:
        """读取某指标各经济体最近两期的值，返回 {economy: (latest, prev)}。若不足两期，prev 为 None。"""
        result: dict[str, list[float]] = {}
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            # 先按 economy 分组，再按日期倒序取两条
            cur.execute(
                "SELECT economy, date, value FROM macro_series WHERE indicator = ? ORDER BY economy, date DESC",
                (indicator,),
            )
            for eco, _d, v in cur.fetchall():
                if v is None:
                    continue
                key = str(eco)
                lst = result.setdefault(key, [])
                if len(lst) < 2:
                    lst.append(float(v))
        out: dict[str, tuple[Optional[float], Optional[float]]] = {}
        for eco, vals in result.items():
            latest = vals[0] if len(vals) >= 1 else None
            prev = vals[1] if len(vals) >= 2 else None
            out[eco] = (latest, prev)
        return out

    def has_any_data(self) -> bool:
        """判断是否已有任一宏观数据。"""
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(1) FROM macro_series", ())
            cnt = cur.fetchone()[0]
        return bool(cnt and cnt > 0)

    def upsert_score(self, view: str, entity_type: str, entity_id: str, date: str, score: float, components_json: str | None = None) -> None:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                (
                    "INSERT OR REPLACE INTO scores (view, entity_type, entity_id, date, score, components_json) "
                    "VALUES (?, ?, ?, ?, ?, ?)"
                ),
                (view, entity_type, entity_id, date, float(score), components_json),
            )
            conn.commit()

    def record_refresh(self, source: str, refreshed_at: str, rows: int) -> None:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO refresh_meta (source, refreshed_at, rows) VALUES (?, ?, ?)",
                (source, refreshed_at, int(rows)),
            )
            conn.commit()

    def get_refresh_status(self) -> dict[str, list[dict[str, str]]]:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT source, refreshed_at, rows FROM refresh_meta ORDER BY id DESC LIMIT 10")
            rows = cur.fetchall()
        return {"history": [{"source": str(s), "refreshed_at": str(ts), "rows": str(r)} for (s, ts, r) in rows]}

